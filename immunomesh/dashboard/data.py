"""Dashboard data layer: loads a demo-run directory and computes every displayed quantity (no UI code)."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd


class RunData:
    def __init__(self, run_dir: str | Path) -> None:
        d = Path(run_dir)
        if not (d / "epochs.csv").exists():
            raise FileNotFoundError(f"no demo run in {d}; run `python -m immunomesh.cli demo` first")
        self.dir = d
        self.epochs = pd.read_csv(d / "epochs.csv")
        self.flows = pd.read_csv(d / "flows.csv")
        self.events = pd.read_csv(d / "events.csv") if (d / "events.csv").stat().st_size > 5 else pd.DataFrame()
        self.evidence = pd.read_csv(d / "evidence.csv")
        self.meta = json.loads((d / "meta.json").read_text())
        self.windows = json.loads((d / "attack_windows.json").read_text())

    def overview(self) -> dict:
        ev, ep = self.events, self.epochs
        et = ev["event_type"].value_counts().to_dict() if len(ev) else {}
        q = et.get("QUARANTINE_STARTED", 0) + et.get("RECOVERY_FAILED_REQUARANTINE", 0)
        return {"monitored_devices": int(ep.device.nunique()), "total_flows": int(len(self.flows)),
                "normal_events": int((self.flows.is_anomaly == 0).sum()),
                "anomalous_events": int((self.flows.is_anomaly == 1).sum()),
                "high_risk_events": int(et.get("HIGH_RISK_DECLARED", 0)),
                "quarantine_events": int(q),
                "devices_quarantined": int(ev[ev.event_type.isin(["QUARANTINE_STARTED", "RECOVERY_FAILED_REQUARANTINE"])].device.nunique()) if len(ev) else 0,
                "recovered_events": int(et.get("RESTORED", 0))}

    def anomaly_by_device(self) -> pd.DataFrame:
        return self.flows.groupby("device").agg(flows=("is_anomaly", "size"), anomalous=("is_anomaly", "sum"),
                                                mean_score=("anomaly_score", "mean")).reset_index()

    def trust_series(self) -> pd.DataFrame:
        return self.epochs[["device", "epoch", "t_start", "trust", "peer_support", "consensus", "risk_level", "state"]]

    def top_features(self, k: int = 10) -> pd.DataFrame:
        rows = []
        for s in self.evidence.top_features:
            for e in json.loads(s):
                rows.append((e["feature"], e["contribution"]))
        if not rows: return pd.DataFrame(columns=["feature", "mean_contribution", "count"])
        d = pd.DataFrame(rows, columns=["feature", "c"])
        return d.groupby("feature").c.agg(mean_contribution="mean", count="size").reset_index().sort_values("count", ascending=False).head(k)

    def audit_events(self, device: str | None = None, event_type: str | None = None) -> pd.DataFrame:
        con = sqlite3.connect(self.dir / "audit.db")
        df = pd.read_sql_query("SELECT * FROM events ORDER BY ts, id", con)
        con.close()
        if device: df = df[df.device == device]
        if event_type: df = df[df.event_type == event_type]
        return df

    def state_matrix(self) -> pd.DataFrame:
        return self.epochs.pivot(index="device", columns="epoch", values="state")
