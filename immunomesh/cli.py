"""Command line entry point:  python -m immunomesh.cli run [--config PATH] [--seed N] [--intensity low|high]"""
import argparse, json
from pathlib import Path
from immunomesh.config import load_config
from immunomesh.logging_utils import setup_logging
from immunomesh.pipeline import run_detection_pipeline


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="immunomesh")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Phases 2-5 only: simulate -> preprocess -> features -> detect -> evaluate")
    r.add_argument("--config", default=None)
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--intensity", choices=["low", "high"], default=None)
    r.add_argument("--out", default="results")

    d = sub.add_parser("demo", help="Full system (Phases 2-9) on one seed; writes results/final/demo for the dashboard")
    d.add_argument("--seed", type=int, default=200)
    d.add_argument("--out", default="results/final/demo")

    dash = sub.add_parser("dashboard", help="Launch the Streamlit research dashboard")
    dash.add_argument("--run-dir", default="results/final/demo")

    inv = sub.add_parser("investigate", help="Phase 6: multi-seed brute-force recall investigation")

    fin = sub.add_parser("final", help="Phase 10: multi-seed experiments 1-10 + ablation + model comparison")
    fin.add_argument("--seeds", type=int, nargs="+", default=None)
    fin.add_argument("--out", default="results/final")
    fin.add_argument("--train-s", type=float, default=None)
    fin.add_argument("--eval-s", type=float, default=None)

    rep = sub.add_parser("report", help="Aggregate results/final/_seeds/*.json into tables, figures, RESULTS.md")
    rep.add_argument("--dir", default="results/final")

    # --- Real-network integration layer (additive; Phases 1-10 commands above are unchanged) ---
    doc = sub.add_parser("doctor", help="Deployment readiness check for the real-network layer")
    doc.add_argument("--config", default=None)

    disc = sub.add_parser("discover", help="Passive device discovery (ARP table + mDNS if available); sends no probes")

    capt = sub.add_parser("capture", help="Capture real traffic on an interface for a fixed duration and print flows")
    capt.add_argument("--interface", default=None)
    capt.add_argument("--duration", type=float, default=5.0)

    mon = sub.add_parser("monitor", help="Foreground OBSERVE_ONLY monitoring loop, fixed number of cycles")
    mon.add_argument("--interface", default=None)
    mon.add_argument("--cycles", type=int, default=10)
    mon.add_argument("--interval", type=float, default=1.0)
    mon.add_argument("--baseline-flows", type=int, dest="baseline_flows", default=20)
    mon.add_argument("--idle-timeout", type=float, dest="idle_timeout", default=None,
                     help="seconds of inactivity before a flow closes (default: feature window + 5s)")

    edge = sub.add_parser("edge", help="Headless edge runtime: capture -> detect -> evidence -> audit, supervised")
    edge.add_argument("--interface", default=None)
    edge.add_argument("--headless", action="store_true", default=True)
    edge.add_argument("--foreground", dest="headless", action="store_false")
    edge.add_argument("--cycles", type=int, default=None)
    edge.add_argument("--interval", type=float, default=1.0)
    edge.add_argument("--baseline-flows", type=int, dest="baseline_flows", default=20)
    edge.add_argument("--idle-timeout", type=float, dest="idle_timeout", default=None,
                      help="seconds of inactivity before a flow closes (default: feature window + 5s)")

    dev = sub.add_parser("devices", help="List devices recorded by discovery/capture so far")

    capa = sub.add_parser("capabilities", help="Report configured switch/AP adapter capabilities")
    capa.add_argument("--config", default=None)

    dry = sub.add_parser("dry-run", help="Simulate an enforcement action (isolate/restore) without touching any adapter")
    dry.add_argument("--device", required=True)
    dry.add_argument("--from-state", dest="from_state", default="HIGH_RISK")
    dry.add_argument("--to-state", dest="to_state", default="QUARANTINED")

    enf = sub.add_parser("enforce", help="Real enforcement — refuses unless config/live.yaml explicitly enables it")
    enf.add_argument("--config", default=None)
    enf.add_argument("--device", default=None)

    stat = sub.add_parser("status", help="One-shot summary: mode, health, interface")
    stat.add_argument("--config", default=None)
    stat.add_argument("--interface", default=None)

    setup = sub.add_parser("setup", help="Detect interfaces/gateway/capture capability and write immunomesh.yaml")
    setup.add_argument("--out", default="immunomesh.yaml")

    a = p.parse_args(argv)
    if a.cmd == "run":
        ov = {}
        if a.seed is not None: ov["seed"] = a.seed
        if a.intensity: ov["simulation"] = {"intensity": a.intensity}
        cfg = load_config(a.config, ov)
        out = Path(a.out) / f"run_seed{cfg.seed}_{cfg.simulation.intensity}"
        setup_logging(out / "run.log")
        res = run_detection_pipeline(cfg, out)
        print(json.dumps({k: res["metrics"][k] for k in ("detection", "per_attack_recall")}, indent=2))
    elif a.cmd == "demo":
        from immunomesh.experiments.demo import run_demo
        from immunomesh.safe_io import UnsafeOutputDir
        setup_logging()
        try:
            out = run_demo(seed=a.seed, out_dir=a.out)
        except UnsafeOutputDir as e:
            raise SystemExit(f"error: {e}")
        print(f"demo written to {out}")
    elif a.cmd == "dashboard":
        import os, subprocess, sys as _sys
        env = {**os.environ, "IMMUNOMESH_RUN_DIR": a.run_dir}
        subprocess.run([_sys.executable, "-m", "streamlit", "run", "immunomesh/dashboard/app.py"], env=env)
    elif a.cmd == "investigate":
        from immunomesh.experiments.investigate import run as run_investigate
        setup_logging()
        run_investigate()
    elif a.cmd == "final":
        from immunomesh.experiments.final import run_all, FINAL_SEEDS
        setup_logging(Path(a.out) / "run.log")
        ov = {}
        if a.train_s or a.eval_s:
            ov["simulation"] = {}
            if a.train_s: ov["simulation"]["train_duration_s"] = a.train_s
            if a.eval_s: ov["simulation"]["eval_duration_s"] = a.eval_s
        run_all(a.seeds or FINAL_SEEDS, a.out, ov or None)
    elif a.cmd == "report":
        from immunomesh.experiments.report import build_report
        build_report(a.dir)
    elif a.cmd == "doctor":
        from immunomesh.integration.cli_commands import cmd_doctor
        cmd_doctor(a)
    elif a.cmd == "discover":
        from immunomesh.integration.cli_commands import cmd_discover
        cmd_discover(a)
    elif a.cmd == "capture":
        from immunomesh.integration.cli_commands import cmd_capture
        cmd_capture(a)
    elif a.cmd == "monitor":
        from immunomesh.integration.cli_commands import cmd_monitor
        cmd_monitor(a)
    elif a.cmd == "edge":
        from immunomesh.integration.cli_commands import cmd_edge
        cmd_edge(a)
    elif a.cmd == "devices":
        from immunomesh.integration.cli_commands import cmd_devices
        cmd_devices(a)
    elif a.cmd == "capabilities":
        from immunomesh.integration.cli_commands import cmd_capabilities
        cmd_capabilities(a)
    elif a.cmd == "dry-run":
        from immunomesh.integration.cli_commands import cmd_dry_run
        cmd_dry_run(a)
    elif a.cmd == "enforce":
        from immunomesh.integration.cli_commands import cmd_enforce
        cmd_enforce(a)
    elif a.cmd == "status":
        from immunomesh.integration.cli_commands import cmd_status
        cmd_status(a)
    elif a.cmd == "setup":
        from immunomesh.integration.cli_commands import cmd_setup
        cmd_setup(a)


if __name__ == "__main__":
    main()
