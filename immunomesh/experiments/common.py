"""Small helpers shared by experiment scripts."""
from __future__ import annotations
import numpy as np
import pandas as pd


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for _, r in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in r]
        body += "| " + " | ".join(cells) + " |\n"
    return head + body


def mean_std(df: pd.DataFrame, by: list[str], cols: list[str]) -> pd.DataFrame:
    g = df.groupby(by)[cols].agg(["mean", "std"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g.reset_index()
