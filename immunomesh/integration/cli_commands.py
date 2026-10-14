"""Implementations for the real-network CLI commands (Section 13). Kept separate from
immunomesh/cli.py so the existing simulation commands stay easy to read; wired in there."""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
import yaml
from immunomesh.integration.capture.interface import default_interface, list_interfaces
from immunomesh.integration.capture.raw_socket import RawSocketCaptureAdapter
from immunomesh.integration.capture.flow import FlowAggregator
from immunomesh.integration.config import LiveConfig, load_live_config
from immunomesh.integration.devices.registry import DeviceRegistry
from immunomesh.integration.discovery.arp import ARPDiscovery
from immunomesh.integration.discovery.mdns import MDNSDiscovery
from immunomesh.integration.enforcement.executor import Executor
from immunomesh.integration.enforcement.policy import propose
from immunomesh.integration.hardware_detect import default_gateway, detect_raspberry_pi, local_ip_for
from immunomesh.integration.health.checks import run_all as run_health_checks
from immunomesh.integration.runtime.live import LiveRuntime
from immunomesh.integration.runtime.supervisor import Supervisor
from immunomesh.integration.security.permissions import check_raw_socket
from immunomesh.integration.status import HealthState, OpStatus, RuntimeMode
from immunomesh.integration.switch.dry_run import DryRunSwitchAdapter


def _pass(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def cmd_doctor(args) -> None:
    print("=" * 40)
    print("     IMMUNOMESH DEPLOYMENT DOCTOR")
    print("=" * 40)
    checks = run_health_checks()
    for c in checks:
        print(f"{c.name.replace('_', ' ').title():<26}{'PASS' if c.state == HealthState.HEALTHY else 'DEGRADED' if c.state == HealthState.DEGRADED else 'FAIL':<10}{c.detail}")

    print("\nHardware:")
    is_pi, pi_detail = detect_raspberry_pi()
    print(f"{'Raspberry Pi':<26}{'DETECTED' if is_pi else 'NOT DETECTED':<14}{pi_detail}")
    arp = ARPDiscovery()
    devices = arp.discover() if arp.status() == OpStatus.LIVE else []
    print(f"{'IP Camera':<26}{'NOT CHECKED (doctor sends no probes; cameras are classified from observed traffic once capture/monitor/edge has run)':<14}")
    print(f"{'Managed Switch':<26}{'NOT CONFIGURED (see config/live.yaml switch: section)':<14}")

    cfg = load_live_config(args.config)
    print("\nCapabilities:")
    raw = check_raw_socket()
    print(f"{'Packet Capture':<26}{'SUPPORTED' if raw.ok else 'UNSUPPORTED':<12}{raw.detail}")
    print(f"{'Switch adapter':<26}{'NOT CONFIGURED' if cfg.switch.adapter == 'none' else cfg.switch.adapter.upper()}")
    print(f"{'Rollback':<26}{'DRY-RUN ONLY (no real switch configured to verify a real rollback against)'}")

    print("\nSafety:")
    print(f"{'Mode':<26}{cfg.runtime_mode().value}")
    print(f"{'Enforcement':<26}{'ENABLED' if cfg.enforcement.enabled else 'DISABLED'}")

    failed = any(c.state == HealthState.FAILED for c in checks)
    status = "READY FOR OBSERVATION" if not failed and raw.ok else \
             "OBSERVATION LIMITED (packet capture unsupported — check permissions)" if not failed else \
             "NOT READY — see FAIL entries above"
    print(f"\nSTATUS:\n{status}")


def cmd_discover(args) -> None:
    print("DEVICE DISCOVERY\n")
    arp = ARPDiscovery()
    found = arp.discover() if arp.status() == OpStatus.LIVE else []
    if arp.status() != OpStatus.LIVE:
        print(f"(ARP discovery unavailable: {arp.status().value})")
    mdns = MDNSDiscovery()
    if mdns.status() != OpStatus.LIVE:
        print(f"(mDNS discovery unavailable: {mdns.status().value} — install `zeroconf` to enable)\n")
    if not found:
        print("No devices found in the ARP table yet. This lists what the kernel already knows —")
        print("it does not send any probes. Run `capture` for a while first to populate it via traffic.")
        return
    for d in found:
        print(f"{d.ip}\n  MAC: {d.mac}\n  Source: {d.source}\n  Confidence: {d.confidence:.2f}\n")


def cmd_capture(args) -> None:
    iface = args.interface or default_interface()
    if not iface:
        print("No network interface found."); return
    print(f"Capturing on {iface} for {args.duration}s ...")
    cap = RawSocketCaptureAdapter(iface, timeout_s=0.3)
    if cap.status() != OpStatus.LIVE:
        print(f"Capture unavailable: {cap.error()}"); return
    agg = FlowAggregator(idle_timeout_s=args.duration + 1)
    t_end, n = time.time() + args.duration, 0
    while time.time() < t_end:
        pkt = cap.recv_one()
        if pkt is not None:
            agg.add(pkt); n += 1
    cap.stop()
    flows = agg.expire(time.time(), force_all=True)
    print(f"\nCaptured {n} packets -> {len(flows)} flows")
    for f in flows[:20]:
        print(f"  {f.src_id:<15} -> {f.dst_id:<15} {f.protocol:<4} {f.src_port}->{f.dst_port}  "
              f"{f.packet_count} pkts, {f.byte_count} bytes, {f.duration_s:.3f}s, failed={f.failed_conn}")


def _build_runtime(args) -> LiveRuntime:
    iface = args.interface or default_interface()
    cap = RawSocketCaptureAdapter(iface, timeout_s=0.3)
    if cap.status() != OpStatus.LIVE:
        raise SystemExit(f"capture unavailable on {iface}: {cap.error()}")
    return LiveRuntime(cap, baseline_min_flows=args.baseline_flows,
                       audit_db="results/live/audit.db", registry_db="results/live/devices.db",
                       idle_timeout_s=getattr(args, "idle_timeout", None))


def cmd_monitor(args) -> None:
    rt = _build_runtime(args)
    sup = Supervisor(rt)
    print(f"Monitoring on {rt.capture.interface} — mode OBSERVE_ONLY (no enforcement in `monitor`).")
    try:
        for i in range(args.cycles):
            r = sup.cycle()
            print(f"[{i+1}/{args.cycles}] health={r['health']:<10} {r}")
            time.sleep(args.interval)
    finally:
        rt.shutdown()


def cmd_edge(args) -> None:
    rt = _build_runtime(args)
    sup = Supervisor(rt)
    mode = "headless" if args.headless else "foreground"
    print(f"ImmunoMesh edge runtime ({mode}) starting on {rt.capture.interface}.")
    print("Mode: OBSERVE_ONLY. Enforcement is never enabled by `edge` — use `enforce` explicitly.")
    try:
        n = 0
        while args.cycles is None or n < args.cycles:
            r = sup.cycle()
            if not args.headless:
                print(f"cycle {n}: health={r['health']} {r}")
            n += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        rt.shutdown()
        print(f"\nstopped after {sup.state.total_cycles} cycles "
              f"({sup.state.total_failures} failures, final health={sup.state.health.value})")


def cmd_devices(args) -> None:
    reg = DeviceRegistry("results/live/devices.db")
    if not reg.devices:
        try:
            import sqlite3
            con = sqlite3.connect("results/live/devices.db")
            rows = con.execute("SELECT ip, mac, device_type, confidence, sources, last_seen FROM devices").fetchall()
            con.close()
        except Exception:
            rows = []
        if not rows:
            print("No devices recorded yet. Run `capture`, `monitor`, or `edge` first."); return
        for ip, mac, dtype, conf, sources, last_seen in rows:
            print(f"{ip:<15} mac={mac or '?':<18} type={dtype:<10} confidence={conf:.2f}  sources={sources}")
        return
    print(reg.as_dataframe().to_string(index=False))


def cmd_capabilities(args) -> None:
    cfg = load_live_config(args.config)
    adapter = DryRunSwitchAdapter()
    caps = adapter.get_capabilities()
    print(f"Switch adapter: {cfg.switch.adapter} (status: {adapter.status().value})")
    for cap, status in caps.items():
        print(f"  {cap.value:<18} {status.value}")


def cmd_dry_run(args) -> None:
    adapter = DryRunSwitchAdapter()
    ex = Executor(RuntimeMode.DRY_RUN, adapter=adapter, dry_run_adapter=adapter)
    proposed = propose(args.device, args.to_state, args.from_state)
    rec = ex.execute(proposed)
    print(f"DRY RUN: {proposed.action} on {args.device} ({proposed.reason})")
    print(f"  -> stage={rec.stage.value}  detail={rec.detail}")


def cmd_enforce(args) -> None:
    cfg = load_live_config(args.config)
    if not cfg.enforcement.enabled or cfg.runtime_mode() != RuntimeMode.ENFORCE:
        print("REFUSED: enforcement is disabled in config/live.yaml (runtime.mode must be 'enforce'")
        print("and enforcement.enabled must be true). This is Rule 3: never silently enter ENFORCE mode.")
        return
    print("No real switch/AP adapter is configured in this deployment (switch.adapter: none).")
    print("Nothing to enforce against. Configure switch.adapter (snmp|ssh) and credentials first.")


def cmd_status(args) -> None:
    cfg = load_live_config(args.config)
    print(f"Mode: {cfg.runtime_mode().value}")
    print(f"Enforcement: {'ENABLED' if cfg.enforcement.enabled else 'DISABLED'}")
    iface = args.interface or default_interface()
    print(f"Default interface: {iface}")
    checks = run_health_checks()
    for c in checks:
        print(f"  {c.name:<20} {c.state.value}")


def cmd_setup(args) -> None:
    ifaces = list_interfaces()
    iface = default_interface()
    ip, gw = local_ip_for(), default_gateway()
    is_pi, pi_detail = detect_raspberry_pi()
    raw = check_raw_socket()
    print("IMMUNOMESH SETUP WIZARD\n")
    print(f"Interfaces found : {[i.name for i in ifaces]}")
    print(f"Selected interface: {iface}")
    print(f"Local IP          : {ip}")
    print(f"Default gateway   : {gw}")
    print(f"Raspberry Pi      : {'yes' if is_pi else 'no'} ({pi_detail})")
    print(f"Capture capability: {'supported' if raw.ok else 'unsupported'} ({raw.detail})")

    cfg = LiveConfig()
    cfg.capture.interface = iface
    out_path = Path(args.out)
    out_path.write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=False))
    print(f"\nWrote {out_path} (runtime.mode=observe_only, enforcement disabled — the safe default).")
    print("Review it, then run `python -m immunomesh.cli doctor` to confirm readiness.")
