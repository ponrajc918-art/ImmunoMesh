"""Data cleaning + quality report (Phase 3)."""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from immunomesh.schema import RAW_COLUMNS, PROTOCOLS

log = logging.getLogger("immunomesh.preprocessing")
IMPUTE_COLS = ["packet_count", "byte_count", "duration_s"]


class DataCleaner:
    """Fit on training data (learns imputation medians), then transform any raw flow table.

    Steps: schema check -> timestamp parsing/sorting -> duplicate removal -> invalid-record
    removal -> median imputation (per device_type, medians learned on training data).
    """

    def __init__(self) -> None:
        self.medians_: dict[str, dict[str, float]] | None = None
        self.global_medians_: dict[str, float] | None = None

    def fit(self, df: pd.DataFrame) -> "DataCleaner":
        valid = self._drop_invalid(self._basic(df))[0]
        self.global_medians_ = {c: float(valid[c].median()) for c in IMPUTE_COLS}
        self.medians_ = {t: {c: float(g[c].median()) for c in IMPUTE_COLS}
                         for t, g in valid.groupby("device_type")}
        return self

    @staticmethod
    def _basic(df: pd.DataFrame) -> pd.DataFrame:
        missing = set(RAW_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")
        out = df[RAW_COLUMNS].copy()
        out["timestamp"] = pd.to_numeric(out["timestamp"], errors="coerce")
        return out

    @staticmethod
    def _drop_invalid(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        # invalid = known-bad values (missing values are imputed, not dropped)
        bad = (
            df["timestamp"].isna()
            | (df["byte_count"] < 0) | (df["packet_count"] < 0) | (df["duration_s"] <= 0)
            | ~df["protocol"].isin(PROTOCOLS)
            | (df["dst_port"].notna() & ((df["dst_port"] < 0) | (df["dst_port"] > 65535)))
        )
        return df[~bad], int(bad.sum())

    def transform(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        if self.medians_ is None:
            raise RuntimeError("DataCleaner must be fit before transform")
        out = self._basic(df)
        report = {"rows_in": len(out)}
        n0 = len(out)
        out = out.drop_duplicates().reset_index(drop=True)
        report["duplicates_removed"] = n0 - len(out)
        out, n_bad = self._drop_invalid(out)
        report["invalid_removed"] = n_bad
        report["missing_values_imputed"] = int(out[IMPUTE_COLS].isna().sum().sum())
        for c in IMPUTE_COLS:
            fill = out["device_type"].map({t: v[c] for t, v in self.medians_.items()})
            out[c] = out[c].fillna(fill).fillna(self.global_medians_[c])
        out = out.sort_values("timestamp", kind="stable").reset_index(drop=True)
        report["rows_out"] = len(out)
        log.info("cleaning report: %s", report)
        return out, report
