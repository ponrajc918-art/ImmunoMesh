"""SQLite audit store (Phase 9): events + per-epoch records, keyed by experiment_id."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments(experiment_id TEXT PRIMARY KEY, seed INTEGER, config_json TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT, ts REAL, device TEXT,
  event_type TEXT, detection_score REAL, evidence TEXT, trust REAL, peer_support REAL, consensus REAL,
  risk_level TEXT, state_from TEXT, state_to TEXT, response TEXT, details TEXT);
CREATE INDEX IF NOT EXISTS ix_events_exp ON events(experiment_id, ts);
CREATE TABLE IF NOT EXISTS epochs(experiment_id TEXT, device TEXT, epoch INTEGER, t_start REAL, n_flows INTEGER,
  n_anom INTEGER, n_conf INTEGER, max_score REAL, severity REAL, trust REAL, peer_support REAL, consensus REAL,
  agreement REAL, risk_level TEXT, state TEXT, alert INTEGER, truth_attack INTEGER, attack_type TEXT);
CREATE INDEX IF NOT EXISTS ix_epochs_exp ON epochs(experiment_id, device, epoch);
"""


class AuditStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path))
        self.con.executescript(SCHEMA)

    def register_experiment(self, experiment_id: str, seed: int, config: dict) -> None:
        self.con.execute("INSERT OR REPLACE INTO experiments VALUES (?,?,?)", (experiment_id, seed, json.dumps(config)))
        self.con.commit()

    def log_events(self, experiment_id: str, events: list[dict]) -> None:
        cols = ["ts", "device", "event_type", "detection_score", "evidence", "trust", "peer_support",
                "consensus", "risk_level", "state_from", "state_to", "response", "details"]
        rows = [(experiment_id,) + tuple(_py(e.get(c)) for c in cols) for e in events]
        self.con.executemany(f"INSERT INTO events(experiment_id,{','.join(cols)}) VALUES (?,{','.join('?'*len(cols))})", rows)
        self.con.commit()

    def log_epochs(self, experiment_id: str, epochs: pd.DataFrame) -> None:
        cols = ["device", "epoch", "t_start", "n_flows", "n_anom", "n_conf", "max_score", "severity", "trust",
                "peer_support", "consensus", "agreement", "risk_level", "state", "alert", "truth_attack", "attack_type"]
        df = epochs.reindex(columns=cols)
        rows = [(experiment_id,) + tuple(_py(v) for v in r) for r in df.itertuples(index=False)]
        self.con.executemany(f"INSERT INTO epochs VALUES (?,{','.join('?'*len(cols))})", rows)
        self.con.commit()

    def events(self, experiment_id: str | None = None) -> pd.DataFrame:
        q, a = "SELECT * FROM events", ()
        if experiment_id: q, a = q + " WHERE experiment_id=?", (experiment_id,)
        return pd.read_sql_query(q + " ORDER BY ts, id", self.con, params=a)

    def epochs(self, experiment_id: str | None = None) -> pd.DataFrame:
        q, a = "SELECT * FROM epochs", ()
        if experiment_id: q, a = q + " WHERE experiment_id=?", (experiment_id,)
        return pd.read_sql_query(q, self.con, params=a)

    def close(self) -> None:
        self.con.close()


def _py(v):
    try:
        import numpy as np
        if isinstance(v, (np.integer,)): return int(v)
        if isinstance(v, (np.floating,)): return None if v != v else float(v)
        if isinstance(v, (np.bool_,)): return int(v)
    except Exception:
        pass
    if isinstance(v, bool): return int(v)
    if isinstance(v, float) and v != v: return None
    return v
