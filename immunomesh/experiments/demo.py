"""Single fully-instrumented run (E3-style scenario, full system) that feeds the dashboard and trajectory figures."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import yaml
from immunomesh.config import load_config
from immunomesh.experiments.scenario import prepare_seed, prepare_scenario, run_variant, ABLATION
from immunomesh.storage.audit import AuditStore
from immunomesh.evidence.explainer import format_evidence
from immunomesh.mesh.engine import n_epochs_for
from immunomesh.safe_io import prepare_output_dir

DEMO_FILES = ("audit.db", "epochs.csv", "events.csv", "flows.csv", "evidence.csv", "attack_windows.json",
              "config.yaml", "meta.json", "evidence_examples.md")


def _is_previous_demo(d: Path) -> bool:
    try:
        return str(json.loads((d / "meta.json").read_text()).get("experiment_id", "")).startswith("demo_")
    except (OSError, ValueError):
        return False


def run_demo(seed: int = 200, out_dir: str | Path = "results/final/demo", overrides: dict | None = None) -> Path:
    out = prepare_output_dir(out_dir, _is_previous_demo, DEMO_FILES)
    cfg = load_config(overrides={"seed": seed, **(overrides or {})})
    sc = prepare_seed(cfg)
    sd = prepare_scenario(sc)
    res = run_variant(sc, sd, ABLATION["A4_full_system"])
    ep, events = res["epochs"], res["events"]
    exp_id = f"demo_seed{seed}"
    audit = AuditStore(out / "audit.db")
    audit.register_experiment(exp_id, seed, res["cfg"].to_dict())
    audit.log_events(exp_id, events)
    audit.log_epochs(exp_id, ep)
    audit.close()
    ep.to_csv(out / "epochs.csv", index=False)
    pd.DataFrame(events).to_csv(out / "events.csv", index=False)
    p, f = sd.ev["pred"], sd.ev["eval_f"]
    flows = p[["device", "timestamp", "anomaly_score", "is_anomaly", "confidence", "anomaly_status", "label", "attack_type"]].copy()
    flows["protocol"] = f["protocol"].to_numpy(); flows["dst_id"] = f["dst_id"].to_numpy()
    flows.to_csv(out / "flows.csv", index=False)
    sd.evidence.to_csv(out / "evidence.csv", index=False)
    (out / "attack_windows.json").write_text(json.dumps({d: [list(w) for w in ws] for d, ws in sd.ev["windows"].items()}, indent=2))
    (out / "config.yaml").write_text(yaml.safe_dump(res["cfg"].to_dict()))
    meta = {"experiment_id": exp_id, "seed": seed, "threshold": sc.ctx.det.threshold_, "metrics": res["metrics"],
            "timing": res["timing"], "n_epochs": n_epochs_for(cfg.simulation.eval_duration_s, cfg.mesh.epoch_s),
            "note": "SIMULATED/SYNTHETIC single illustrative run; software time only."}
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=float))
    lines = ["# Evidence examples (auto-generated from the demo run; synthetic data)\n"]
    E = sd.evidence
    for kind in ["traffic_spike", "port_scan", "brute_force", "exfiltration", "protocol_irregularity"]:
        g = E[(E.label == 1) & (E.attack_type == kind)]
        if len(g): lines += [f"## {kind}\n", "```", format_evidence(g.iloc[len(g) // 2], sc.ctx.det.threshold_), "```\n"]
    g = E[E.label == 0]
    if len(g): lines += ["## false positive (normal flow flagged)\n", "```", format_evidence(g.iloc[0], sc.ctx.det.threshold_), "```\n"]
    (out / "evidence_examples.md").write_text("\n".join(lines))
    return out
