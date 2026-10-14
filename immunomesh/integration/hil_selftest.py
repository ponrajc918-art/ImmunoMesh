"""HIL self-test (Section 20/25/26) — HONEST SCOPE: this runs the real capture/flow/detect
pipeline against REAL packets on this container's own network stack (loopback + locally
generated traffic). It is NOT a test against a physical Raspberry Pi, managed switch, or IP
camera — none were available when this was built (Section 25: 'Do not generate attacks against
networks/devices without authorization', and more basically, no such hardware exists in this
environment). What it DOES prove: the capture -> flow -> schema -> existing Phase 1-5 pipeline
-> evidence -> trust chain runs on genuinely captured traffic, not simulator output, end to end,
with no fabricated numbers — every figure here is measured from this run.
"""
from __future__ import annotations
import json
import socket
import threading
import time
from pathlib import Path
import pandas as pd
from immunomesh.config import load_config
from immunomesh.integration.capture.raw_socket import RawSocketCaptureAdapter
from immunomesh.integration.hardware_detect import detect_raspberry_pi
from immunomesh.integration.runtime.live import LiveRuntime
from immunomesh.integration.runtime.supervisor import Supervisor
from immunomesh.integration.security.permissions import check_raw_socket
from immunomesh.integration.status import OpStatus
from immunomesh.safe_io import prepare_output_dir

HIL_FILES = ("RESULTS.md", "alerts.csv", "audit.db", "devices.csv", "devices.db", "enforcement.csv",
             "performance.csv", "run_manifest.json")


def _is_previous_hil(d: Path) -> bool:
    try:
        return json.loads((d / "run_manifest.json").read_text()).get("mode") == "HIL_SELFTEST"
    except (OSError, ValueError):
        return False


def _generate_background_traffic(duration_s: float, stop_evt: threading.Event) -> int:
    """Real local TCP connections over loopback — genuine packets, not simulator output."""
    count = 0
    t_end = time.time() + duration_s
    while time.time() < t_end and not stop_evt.is_set():
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(("127.0.0.1", 0)); srv.listen(1)
            port = srv.getsockname()[1]
            done = threading.Event()
            def accept():
                try:
                    c, _ = srv.accept(); c.recv(2048); c.sendall(b"ack" * 20); c.close()
                except OSError:
                    pass
                done.set()
            threading.Thread(target=accept, daemon=True).start()
            cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli.connect(("127.0.0.1", port))
            cli.sendall(b"hil-selftest-payload " * 5)
            done.wait(timeout=0.5)
            cli.recv(4096)
            cli.close(); srv.close()
            count += 1
        except OSError:
            pass
        time.sleep(0.15)
    return count


def run(duration_s: float = 20.0, interface: str = "lo", out_dir: str = "results/hil") -> Path:
    out = prepare_output_dir(out_dir, _is_previous_hil, HIL_FILES)

    raw_check = check_raw_socket()
    is_pi, pi_detail = detect_raspberry_pi()
    manifest = {
        "mode": "HIL_SELFTEST",
        "honest_scope": "Real packet capture on this container's own loopback interface, with "
                        "locally generated TCP traffic. NO physical Raspberry Pi, managed switch, "
                        "or IP camera was used or is claimed. This validates the real-capture code "
                        "path end-to-end, not a physical deployment.",
        "interface": interface, "raspberry_pi_detected": is_pi, "raspberry_pi_detail": pi_detail,
        "raw_socket_capability": raw_check.ok, "raw_socket_detail": raw_check.detail,
        "started_at": time.time(), "requested_duration_s": duration_s,
    }
    if not raw_check.ok:
        manifest["status"] = "SKIPPED_UNSUPPORTED"
        (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
        (out / "RESULTS.md").write_text("# HIL self-test SKIPPED\n\nRaw-socket capture is unsupported "
                                        f"in this environment: {raw_check.detail}\n")
        return out

    stop_evt = threading.Event()
    gen_thread = threading.Thread(target=lambda: manifest.__setitem__(
        "real_connections_generated", _generate_background_traffic(duration_s, stop_evt)), daemon=True)
    gen_thread.start()

    cap = RawSocketCaptureAdapter(interface, timeout_s=0.3)
    cfg = load_config()
    rt = LiveRuntime(cap, cfg=cfg, baseline_min_flows=5, idle_timeout_s=0.8,
                     audit_db=str(out / "audit.db"), registry_db=str(out / "devices.db"))
    sup = Supervisor(rt)

    cycles, t_end = [], time.time() + duration_s + 2.0
    while time.time() < t_end:
        r = sup.cycle()
        cycles.append({"ts": time.time(), **r})
        time.sleep(0.5)
    stop_evt.set()
    gen_thread.join(timeout=2.0)
    rt.shutdown()

    perf = {"packets_captured": rt.stats.packets_seen, "flows_closed": rt.stats.flows_closed,
            "dropped_packets": rt.stats.dropped_packets, "epochs_processed": rt.stats.epochs_processed,
            "cycles_run": len(cycles), "supervisor_failures": sup.state.total_failures,
            "final_health": sup.state.health.value, "final_runtime_state": rt.state.value,
            "mean_cycle_latency_ms": sum(c.get("packets_total", 0) for c in cycles) and rt.stats.last_batch_latency_ms}
    manifest.update(perf)
    manifest["completed_at"] = time.time()

    devices_df = rt.registry.as_dataframe()
    devices_df.to_csv(out / "devices.csv", index=False)

    import sqlite3
    con = sqlite3.connect(str(out / "audit.db"))
    events_df = pd.read_sql_query("SELECT * FROM events", con)
    con.close()
    events_df.to_csv(out / "alerts.csv", index=False)
    pd.DataFrame(cycles).to_csv(out / "performance.csv", index=False)
    pd.DataFrame(columns=["device", "action", "status"]).to_csv(out / "enforcement.csv", index=False)  # none performed

    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    _write_results_md(out, manifest, devices_df, events_df)
    return out


def _write_results_md(out: Path, manifest: dict, devices_df, events_df) -> None:
    L = ["# ImmunoMesh HIL self-test results\n",
         "**Scope**: " + manifest["honest_scope"] + "\n",
         f"- Interface: `{manifest['interface']}`",
         f"- Raspberry Pi detected: {manifest['raspberry_pi_detected']} ({manifest['raspberry_pi_detail']})",
         f"- Real TCP connections generated (loopback): {manifest.get('real_connections_generated', 0)}",
         f"- Real packets captured: {manifest['packets_captured']}",
         f"- Flows closed: {manifest['flows_closed']}  ·  Dropped packets: {manifest['dropped_packets']}",
         f"- Supervisor cycles run: {manifest['cycles_run']}  ·  failures: {manifest['supervisor_failures']}  ·  final health: {manifest['final_health']}",
         f"- Final runtime state: {manifest['final_runtime_state']}",
         f"\n## Devices observed ({len(devices_df)})\n", devices_df.to_markdown(index=False) if len(devices_df) else "(none)",
         f"\n## Audit events logged ({len(events_df)})\n",
         events_df[["ts", "device", "event_type", "detection_score", "risk_level"]].to_markdown(index=False) if len(events_df) else "(none)",
         "\n## What this does NOT demonstrate\n",
         "- No physical Raspberry Pi, managed switch, or IP camera was used.\n"
         "- No real-world attacker traffic — only benign locally-generated TCP connections.\n"
         "- Precision, recall and F1 are not reported: real traffic has no ground-truth labels, so any such number would be fabricated.\n"
         "- The live runtime exercised here performs capture, flow aggregation, detection (Isolation Forest fitted on a short live baseline) and trust updates only. Evidence generation runs but is not persisted, and peer consensus, the response state machine and the enforcement executor are NOT wired into this runtime. The `details` text of rows in `alerts.csv`/`audit.db` produced by earlier runs that says a response/enforcement layer 'runs separately' is inaccurate: no such layer was active.\n"
         "- The detector was fitted on a handful of flows from a single loopback host, so its flagged flows are not meaningful detections; this run validates the capture-to-audit data path, nothing about detection quality.\n"
         "- See docs/REAL_NETWORK_GUIDE.md for what a genuine physical HIL run would need."]
    (out / "RESULTS.md").write_text("\n".join(str(x) for x in L))


if __name__ == "__main__":
    from immunomesh.logging_utils import setup_logging
    setup_logging()
    p = run()
    print(f"HIL self-test results written to {p}")
