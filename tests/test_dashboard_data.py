import pandas as pd, pytest
from pathlib import Path
from immunomesh.experiments.demo import run_demo
from immunomesh.dashboard.data import RunData

@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    d = tmp_path_factory.mktemp("demo") / "demo"
    return run_demo(seed=5, out_dir=d, overrides={"simulation": {"train_duration_s": 400, "eval_duration_s": 400}})

def test_demo_files_and_overview(demo):
    d = RunData(demo)
    o = d.overview()
    assert o["monitored_devices"] == 9
    assert o["normal_events"] + o["anomalous_events"] == o["total_flows"] == len(d.flows)
    assert (demo / "audit.db").exists()

def test_audit_matches_events_csv(demo):
    d = RunData(demo)
    assert len(d.audit_events()) == len(d.events)
    assert {"experiment_id", "trust", "consensus", "evidence", "response"} <= set(d.audit_events().columns)

def test_state_matrix_and_features(demo):
    d = RunData(demo)
    assert d.state_matrix().shape[0] == 9
    assert set(d.state_matrix().stack().unique()) <= {"NORMAL","SUSPICIOUS","HIGH_RISK","QUARANTINED","RECOVERING","RESTORED"}
    assert "feature" in d.top_features().columns

def test_streamlit_app_runs(demo, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("IMMUNOMESH_RUN_DIR", str(demo))
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "immunomesh" / "dashboard" / "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception


def test_streamlit_app_has_live_network_tab_and_handles_missing_run(demo, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("IMMUNOMESH_RUN_DIR", str(demo))
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "immunomesh" / "dashboard" / "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 8  # 7 simulation tabs + Live Network
