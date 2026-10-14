"""Regression tests for the v1.0.0 audit finding: `cli demo --out DIR` used to rmtree DIR."""
import json
from pathlib import Path
import pytest
from immunomesh.safe_io import prepare_output_dir, UnsafeOutputDir
from immunomesh.experiments.demo import run_demo, _is_previous_demo, DEMO_FILES
from immunomesh.integration.hil_selftest import _is_previous_hil, HIL_FILES


def test_run_demo_refuses_unrelated_nonempty_dir_and_deletes_nothing(tmp_path):
    (tmp_path / "thesis.txt").write_text("keep me")
    (tmp_path / "sub").mkdir(); (tmp_path / "sub" / "notes.txt").write_text("keep me too")
    with pytest.raises(UnsafeOutputDir):
        run_demo(seed=5, out_dir=tmp_path)           # must fail before doing any work
    assert (tmp_path / "thesis.txt").read_text() == "keep me"
    assert (tmp_path / "sub" / "notes.txt").read_text() == "keep me too"


def test_reuse_of_previous_demo_dir_removes_only_generated_files(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"experiment_id": "demo_seed200"}))
    (tmp_path / "flows.csv").write_text("old")
    (tmp_path / "my_notes.md").write_text("user file")
    prepare_output_dir(tmp_path, _is_previous_demo, DEMO_FILES)
    assert not (tmp_path / "flows.csv").exists() and not (tmp_path / "meta.json").exists()
    assert (tmp_path / "my_notes.md").read_text() == "user file"      # never touched


def test_empty_and_new_directories_are_accepted(tmp_path):
    assert prepare_output_dir(tmp_path, _is_previous_demo, DEMO_FILES) == tmp_path.resolve()
    new = tmp_path / "a" / "b"
    assert prepare_output_dir(new, _is_previous_demo, DEMO_FILES).is_dir()


def test_refuses_cwd_home_root_and_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for bad in (Path.cwd(), Path.home(), Path("/")):
        with pytest.raises(UnsafeOutputDir):
            prepare_output_dir(bad, lambda p: True, ())
    f = tmp_path / "afile"; f.write_text("x")
    with pytest.raises(UnsafeOutputDir):
        prepare_output_dir(f, lambda p: True, ())


def test_hil_marker_requires_hil_mode(tmp_path):
    (tmp_path / "run_manifest.json").write_text(json.dumps({"mode": "SOMETHING_ELSE"}))
    assert not _is_previous_hil(tmp_path)
    (tmp_path / "run_manifest.json").write_text(json.dumps({"mode": "HIL_SELFTEST"}))
    assert _is_previous_hil(tmp_path)
    assert "run_manifest.json" in HIL_FILES
