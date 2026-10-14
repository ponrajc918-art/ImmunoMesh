"""Production Isolation Forest anomaly detector for ImmunoMesh.

Input:
    A finite, numeric pandas DataFrame containing the engineered features
    from an anomaly-free training period.

Scoring:
    anomaly_score = -IsolationForest.score_samples(X)
    Higher scores indicate more anomalous observations.

Decision threshold:
    The configured quantile of the training anomaly scores.

Prediction:
    An observation is ANOMALOUS when its anomaly score exceeds the threshold.

Confidence:
    Distance from the decision threshold, normalized by the difference
    between the threshold and the median training anomaly score.

Reproducibility:
    Uses the configured training sample limit and a fixed random seed.
    If an integer max_samples exceeds the available training observations,
    it is explicitly limited to the available count before fitting.

Persistence:
    Model artifacts are saved atomically to avoid leaving a partially
    written model file following an interrupted save.

Security:
    Model files loaded with joblib must be trusted. Loading an untrusted
    serialized file can execute arbitrary code.
"""

from __future__ import annotations

import os
import tempfile
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from immunomesh.config import DetectorConfig


class AnomalyDetector:
    """Train, evaluate, persist, and load an Isolation Forest detector."""

    def __init__(
        self,
        cfg: DetectorConfig,
        seed: int = 42,
    ) -> None:
        if (
            isinstance(cfg.n_estimators, (bool, np.bool_))
            or not isinstance(cfg.n_estimators, Integral)
            or cfg.n_estimators < 1
        ):
            raise ValueError(
                "n_estimators must be a positive integer."
            )

        try:
            threshold_quantile = float(cfg.threshold_quantile)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "threshold_quantile must be a numeric value in (0, 1)."
            ) from exc

        if (
            not np.isfinite(threshold_quantile)
            or not 0.0 < threshold_quantile < 1.0
        ):
            raise ValueError(
                "threshold_quantile must be strictly between 0 and 1."
            )

        if (
            isinstance(seed, (bool, np.bool_))
            or not isinstance(seed, Integral)
            or seed < 0
        ):
            raise ValueError("seed must be a non-negative integer.")

        self._validate_max_samples(cfg.max_samples)

        self.cfg = cfg
        self.seed = int(seed)
        self._threshold_quantile = threshold_quantile

        self.model = self._new_model(cfg.max_samples)

        self.threshold_: float | None = None
        self.train_median_: float | None = None
        self.columns_: list[Any] | None = None

    @staticmethod
    def _validate_max_samples(value: Any) -> None:
        """Validate the supported scikit-learn max_samples configurations."""

        if isinstance(value, str):
            if value == "auto":
                return

            raise ValueError(
                "max_samples must be 'auto', a positive integer, "
                "or a fraction in (0, 1]."
            )

        if isinstance(value, (bool, np.bool_)):
            raise ValueError(
                "max_samples must not be a boolean."
            )

        if isinstance(value, Integral):
            if value < 1:
                raise ValueError(
                    "Integer max_samples must be at least 1."
                )
            return

        if isinstance(value, Real):
            fraction = float(value)

            if np.isfinite(fraction) and 0.0 < fraction <= 1.0:
                return

        raise ValueError(
            "max_samples must be 'auto', a positive integer, "
            "or a fraction in (0, 1]."
        )

    def _new_model(
        self,
        max_samples: Any,
    ) -> IsolationForest:
        """Construct an estimator using the configured model parameters."""

        return IsolationForest(
            n_estimators=int(self.cfg.n_estimators),
            max_samples=max_samples,
            random_state=self.seed,
            n_jobs=1,
        )

    def _effective_max_samples(
        self,
        n_samples: int,
    ) -> str | int | float:
        """Resolve the sample limit without triggering an oversized-sample warning.

        An integer limit greater than the available training observations
        is reduced to the available count.

        Fractional limits and 'auto' retain their scikit-learn semantics.
        """

        configured = self.cfg.max_samples

        if configured == "auto":
            return "auto"

        if isinstance(configured, Integral):
            return min(int(configured), n_samples)

        return float(configured)

    @staticmethod
    def _feature_matrix(
        X: pd.DataFrame,
        expected_columns: list[Any] | None = None,
    ) -> np.ndarray:
        """Validate a feature DataFrame and convert it to a numeric matrix."""

        if not isinstance(X, pd.DataFrame):
            raise TypeError(
                "Features must be provided as a pandas DataFrame."
            )

        if X.empty:
            raise ValueError(
                "The feature matrix must contain at least one observation "
                "and one feature."
            )

        if not X.columns.is_unique:
            raise ValueError(
                "Feature column names must be unique."
            )

        if expected_columns is not None:
            if list(X.columns) != expected_columns:
                raise ValueError(
                    "Feature columns differ from the training columns. "
                    "The names and order must match exactly."
                )

        try:
            matrix = X.to_numpy(
                dtype=np.float64,
                copy=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "All detector features must contain numeric values."
            ) from exc

        if matrix.ndim != 2 or matrix.shape[1] == 0:
            raise ValueError(
                "The feature matrix must be two-dimensional "
                "and contain at least one feature."
            )

        if not np.isfinite(matrix).all():
            invalid_positions = np.argwhere(~np.isfinite(matrix))
            row_index, column_index = invalid_positions[0]

            feature_name = X.columns[column_index]

            raise ValueError(
                "Non-finite feature value found at row position "
                f"{row_index}, feature {feature_name!r}. "
                "Resolve missing values and infinities during preprocessing."
            )

        return matrix

    def _require_fitted(self) -> None:
        """Reject scoring, prediction, or persistence before successful fitting."""

        if (
            self.columns_ is None
            or self.threshold_ is None
            or self.train_median_ is None
        ):
            raise RuntimeError(
                "The anomaly detector has not been fitted successfully."
            )

    def fit(
        self,
        X: pd.DataFrame,
    ) -> AnomalyDetector:
        """Fit a new detector using an anomaly-free training dataset.

        The existing fitted model is retained if validation or fitting fails.
        """

        matrix = self._feature_matrix(X)

        effective_max_samples = self._effective_max_samples(
            n_samples=matrix.shape[0],
        )

        # Train a candidate model before replacing the current model.
        # This prevents a failed refit from destroying a valid fitted model.
        candidate_model = self._new_model(
            max_samples=effective_max_samples,
        )

        candidate_model.fit(matrix)

        training_scores = -candidate_model.score_samples(matrix)

        if not np.isfinite(training_scores).all():
            raise RuntimeError(
                "Training produced non-finite anomaly scores."
            )

        candidate_threshold = float(
            np.quantile(
                training_scores,
                self._threshold_quantile,
            )
        )

        candidate_median = float(
            np.median(training_scores)
        )

        if (
            not np.isfinite(candidate_threshold)
            or not np.isfinite(candidate_median)
        ):
            raise RuntimeError(
                "Training produced invalid threshold statistics."
            )

        # Publish the new estimator only after training succeeds.
        self.model = candidate_model
        self.columns_ = list(X.columns)
        self.threshold_ = candidate_threshold
        self.train_median_ = candidate_median

        return self

    def score(
        self,
        X: pd.DataFrame,
    ) -> np.ndarray:
        """Return anomaly scores, with higher values indicating anomalies."""

        self._require_fitted()

        matrix = self._feature_matrix(
            X,
            expected_columns=self.columns_,
        )

        scores = -self.model.score_samples(matrix)

        if not np.isfinite(scores).all():
            raise RuntimeError(
                "The detector produced non-finite anomaly scores."
            )

        return scores

    def predict(
        self,
        X: pd.DataFrame,
        meta: pd.DataFrame | None = None,
        threshold: float | None = None,
    ) -> pd.DataFrame:
        """Produce anomaly scores, classifications, and confidence values."""

        self._require_fitted()

        if threshold is None:
            active_threshold = self.threshold_
        else:
            if isinstance(threshold, (bool, np.bool_)):
                raise ValueError(
                    "The prediction threshold must be a finite number."
                )

            try:
                active_threshold = float(threshold)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "The prediction threshold must be a finite number."
                ) from exc

            if not np.isfinite(active_threshold):
                raise ValueError(
                    "The prediction threshold must be a finite number."
                )

        if meta is not None:
            if not isinstance(meta, pd.DataFrame):
                raise TypeError(
                    "Prediction metadata must be a pandas DataFrame."
                )

            required_metadata = {"src_id", "timestamp"}
            missing_metadata = required_metadata - set(meta.columns)

            if missing_metadata:
                raise ValueError(
                    "Prediction metadata is missing required columns: "
                    f"{sorted(missing_metadata)}."
                )

            if len(meta) != len(X):
                raise ValueError(
                    "Prediction metadata and feature rows must have "
                    "the same number of observations."
                )

        scores = self.score(X)

        # Preserve the original ImmunoMesh decision rule and confidence
        # calculation so the detector's established behavior remains intact.
        denominator = max(
            float(active_threshold - self.train_median_),
            1e-9,
        )

        anomaly_flags = (
            scores > active_threshold
        ).astype(np.int32)

        confidence = np.clip(
            np.abs(scores - active_threshold) / denominator,
            0.0,
            1.0,
        )

        predictions = pd.DataFrame(
            {
                "anomaly_score": scores,
                "is_anomaly": anomaly_flags,
                "confidence": confidence,
            }
        )

        predictions["anomaly_status"] = np.where(
            anomaly_flags == 1,
            "ANOMALOUS",
            "NORMAL",
        )

        if meta is not None:
            predictions.insert(
                0,
                "device",
                meta["src_id"].to_numpy(),
            )

            predictions.insert(
                1,
                "timestamp",
                meta["timestamp"].to_numpy(),
            )

        return predictions

    def save(
        self,
        path: str | Path,
    ) -> None:
        """Atomically persist a successfully fitted detector."""

        self._require_fitted()

        destination = Path(path)

        if destination.exists() and destination.is_dir():
            raise IsADirectoryError(
                f"Model destination is a directory: {destination}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(destination.parent),
        )

        os.close(file_descriptor)

        temporary_path = Path(temporary_name)

        try:
            joblib.dump(
                self,
                temporary_path,
            )

            # The temporary file is in the destination directory,
            # allowing an atomic replacement on the same filesystem.
            os.replace(
                temporary_path,
                destination,
            )

        finally:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def load(
        path: str | Path,
    ) -> AnomalyDetector:
        """Load a detector from a trusted serialized model artifact."""

        detector = joblib.load(Path(path))

        if not isinstance(detector, AnomalyDetector):
            raise TypeError(
                "The model artifact does not contain an AnomalyDetector."
            )

        detector._require_fitted()

        return detector