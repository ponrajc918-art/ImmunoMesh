"""Encode + scale engineered features into a model-ready matrix (Phase 3)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from immunomesh.schema import ENGINEERED, PROTOCOLS, DIRECTIONS, DEVICE_TYPES


class FeatureMatrixBuilder:
    """One-hot encodes categoricals (fixed vocabularies) and z-scores numerics.

    The scaler is fit on the anomaly-free training period only, then reused for evaluation.
    """
    cat_vocab = {"protocol": PROTOCOLS, "direction": DIRECTIONS, "device_type": DEVICE_TYPES}

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.columns_: list[str] | None = None

    def _raw(self, feats: pd.DataFrame) -> pd.DataFrame:
        X = feats[ENGINEERED].astype(float).copy()
        for col, vocab in self.cat_vocab.items():
            for v in vocab:
                X[f"{col}={v}"] = (feats[col] == v).astype(float)
        return X

    def fit(self, feats: pd.DataFrame) -> "FeatureMatrixBuilder":
        X = self._raw(feats)
        self._validate(X)
        self.columns_ = list(X.columns)
        self.scaler.fit(X[ENGINEERED])
        return self

    @staticmethod
    def _validate(X: pd.DataFrame) -> None:
        if X.isna().any().any():
            raise ValueError("feature matrix contains NaN")
        if not np.isfinite(X.to_numpy()).all():
            raise ValueError("feature matrix contains inf")

    def transform(self, feats: pd.DataFrame) -> pd.DataFrame:
        if self.columns_ is None:
            raise RuntimeError("FeatureMatrixBuilder must be fit first")
        X = self._raw(feats)
        self._validate(X)
        X[ENGINEERED] = self.scaler.transform(X[ENGINEERED])
        return X[self.columns_]
