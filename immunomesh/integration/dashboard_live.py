"""LIVE NETWORK dashboard data layer (Section 15) — reads results/live or results/hil run
directories. Separate from immunomesh/dashboard/data.py (which reads simulation demo runs) so
simulated and real data are never silently mixed (Section 15/24)."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
import pandas as pd


class LiveRunData:
    def __init__(self, run_dir: str | Path) -> None:
        self.dir = Path(run_dir)
        self.manifest = {}
        mp = self.dir / "run_manifest.json"
        if mp.exists():
            self.manifest = json.loads(mp.read_text())

    def devices(self) -> pd.DataFrame:
        p = self.dir / "devices.csv"
        if p.exists():
            return pd.read_csv(p)
        db = self.dir / "devices.db"
        if db.exists():
            con = sqlite3.connect(str(db))
            df = pd.read_sql_query("SELECT * FROM devices", con)
            con.close()
            return df
        return pd.DataFrame()

    def alerts(self) -> pd.DataFrame:
        p = self.dir / "alerts.csv"
        if p.exists():
            return pd.read_csv(p)
        db = self.dir / "audit.db"
        if db.exists():
            con = sqlite3.connect(str(db))
            df = pd.read_sql_query("SELECT * FROM events ORDER BY ts DESC", con)
            con.close()
            return df
        return pd.DataFrame()

    def performance(self) -> pd.DataFrame:
        p = self.dir / "performance.csv"
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    def health(self) -> dict:
        return {"final_health": self.manifest.get("final_health", "unknown"),
                "cycles_run": self.manifest.get("cycles_run", 0),
                "supervisor_failures": self.manifest.get("supervisor_failures", 0),
                "dropped_packets": self.manifest.get("dropped_packets", 0),
                "mode": self.manifest.get("mode", "unknown")}
