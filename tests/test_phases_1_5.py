import numpy as np, pandas as pd, pytest
from immunomesh.config import load_config, from_dict
from immunomesh.simulation.traffic import generate_traffic
from immunomesh.preprocessing.cleaner import DataCleaner
from immunomesh.preprocessing.matrix import FeatureMatrixBuilder
from immunomesh.features.engineering import FeatureEngineer
from immunomesh.detection.isolation_forest import AnomalyDetector
from immunomesh.pipeline import run_detection_pipeline
from immunomesh.schema import ENGINEERED

@pytest.fixture(scope="module")
def cfg():
    c = load_config(overrides={"simulation": {"train_duration_s": 300, "eval_duration_s": 300}})
    return c

def test_config_validation():
    with pytest.raises(ValueError):
        from_dict({"simulation": {"intensity": "extreme"}})
    with pytest.raises(ValueError):
        from_dict({"detector": {"threshold_quantile": 1.5}})

def test_simulator_reproducible_and_labelled(cfg):
    a = generate_traffic(cfg.simulation, 1, True)
    b = generate_traffic(cfg.simulation, 1, True)
    pd.testing.assert_frame_equal(a, b)
    assert a.label.sum() > 0
    assert generate_traffic(cfg.simulation, 1, False).label.sum() == 0

def test_cleaner_removes_bad_rows(cfg):
    raw = generate_traffic(cfg.simulation, 2, False)
    clean, rep = DataCleaner().fit(raw).transform(raw)
    assert rep["duplicates_removed"] >= 0 and rep["invalid_removed"] > 0
    assert not clean[["packet_count", "byte_count", "duration_s"]].isna().any().any()
    assert (clean.byte_count >= 0).all() and clean.timestamp.is_monotonic_increasing

def test_features_finite_and_complete(cfg):
    raw = generate_traffic(cfg.simulation, 3, False)
    clean, _ = DataCleaner().fit(raw).transform(raw)
    f = FeatureEngineer(10).fit(clean).transform(clean)
    assert set(ENGINEERED) <= set(f.columns)
    X = FeatureMatrixBuilder().fit(f).transform(f)
    assert np.isfinite(X.to_numpy()).all()

def test_detector_train_predict_persist(cfg, tmp_path):
    res = run_detection_pipeline(cfg, tmp_path)
    det = res["detector"]
    det.save(tmp_path / "d.joblib")
    loaded = AnomalyDetector.load(tmp_path / "d.joblib")
    assert loaded.threshold_ == det.threshold_
    assert set(res["pred"].anomaly_status) <= {"NORMAL", "ANOMALOUS"}
    assert (tmp_path / "metrics.json").exists()

def test_pipeline_deterministic(cfg):
    m1 = run_detection_pipeline(cfg)["metrics"]["detection"]
    m2 = run_detection_pipeline(cfg)["metrics"]["detection"]
    assert m1 == m2
