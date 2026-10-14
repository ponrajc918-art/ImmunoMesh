# Reproducibility guide

## 1. Python version
3.12.3 was used to generate `results/final/` and `results/hil/` (recorded in
`results/final/run_manifest.json`) and is the only version tested. `doctor` warns below 3.10; no
other version has been verified.

## 2. Environment setup
```
git clone <this repository>
cd immunomesh_project
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
```

## 3. Dependency installation
```
pip install -r requirements-dev.txt     # everything: simulation, dashboard, tests, experiments
# or, for an edge-only deployment with no dashboard/experiment tooling:
pip install -r requirements-runtime.txt
```
`requirements.txt` is kept as an alias of `requirements-dev.txt` for anyone who runs the obvious
filename. `requirements-dev.txt` is **unpinned**, so a fresh install resolves newer versions than those
that generated the stored results. `requirements-lock.txt` pins all 58 packages in the dependency
closure to the versions of the environment that generated `results/final/` and `results/hil/`
(Python/numpy/pandas/scikit-learn/platform cross-checked against `run_manifest.json`). Use it for the
closest reproduction attempt:
```
pip install -r requirements-lock.txt
```

## 4. Test command
```
pytest -q
```
Expected: **75 passed**, 0 failed, 0 skipped. Real-network-layer tests use mocks/fakes, so no physical
hardware, root privilege or network access is needed. The suite was run and passed (a) with bare
`pytest -q` and no `PYTHONPATH` (as `.github/workflows/ci.yml` runs it), (b) as root and as an
unprivileged user whose raw-socket access was denied, (c) in a venv from `requirements-dev.txt`
(scikit-learn 1.9.1, numpy 2.5.4) and (d) in a venv from `requirements-lock.txt` (scikit-learn 1.8.0,
numpy 2.4.4).

## 5. Experiment command
```
python -m immunomesh.cli final --seeds 200 201 202 203 204 205 206 207 --train-s 900 --eval-s 900
python -m immunomesh.cli report
```
Per-seed results are checkpointed under `results/final/_seeds/seed_<N>.json`; rerunning `final`
skips seeds whose checkpoint file already exists, so interrupting and resuming is safe. `report`
always regenerates `tables/`, `figures/`, and `RESULTS.md` from whatever checkpoints exist.

## 6. Seed configuration
Seeds **200–207** (8 seeds), `train_duration_s=900`, `eval_duration_s=900` (shortened from the
`config/default.yaml` default of 1800s for tractable runtime — documented, not a metric-chasing
change; see `results/final/run_manifest.json`'s `base_config` for the exact resolved
configuration used).

## 7. Where raw/per-seed outputs are stored
`results/final/_seeds/seed_<N>.json` — one file per seed, containing every flow-level and
mesh-level row that seed produced, plus model-comparison and evidence-contribution data for E2/E3.
These are the only inputs `report.py` reads; nothing is aggregated anywhere else first.

## 8. How final tables are generated
`python -m immunomesh.cli report` → `immunomesh/experiments/report.py`, which loads every
`seed_*.json`, pools the flow/mesh rows, and writes `results/final/tables/*.csv` with
`groupby(...).agg(["mean","std"])` — never a hand-typed number.

## 9. How figures are generated
Same `report.py` call, same input data, `matplotlib` → `results/final/figures/*.png`. Regenerate
by deleting the directory and rerunning `report` — never hand-edit a PNG.

## 10. How the dashboard demo is started
```
python -m immunomesh.cli demo --seed 200     # writes results/final/demo/
python -m immunomesh.cli dashboard           # Streamlit app over that run
```

## 11. How HIL testing is performed
```
python -m immunomesh.integration.hil_selftest
```
Runs a **loopback-only** self-test (real packet capture, real local TCP traffic) — see
`results/hil/RESULTS.md` for what this does and does not demonstrate. No physical hardware is
used or required.

## Verification status of these instructions
Checked by running the documented commands, not by inspection: `final --seeds 200` was re-run from
scratch in a fresh venv built from `requirements-dev.txt` (scikit-learn 1.9.1, numpy 2.5.4, shap 0.53,
i.e. *newer* than the lock) and reproduced the stored `seed_200.json` exactly: 1,422 numeric cells
compared (14 flow-level + 55 epoch-level rows, plus per-attack recall and model-comparison F1), maximum
absolute difference 0.0; wall-clock timing fields excluded. Seeds 201-207 were not re-run in that
environment. This demonstrates repeatability of the same seeded code on the same OS/architecture
(Linux x86_64); it is **not** independent replication, and cross-platform or cross-BLAS bit-identity is
untested.

## 12. Important limitations
See `docs/LIMITATIONS.md` for the full list. Headline items: exfiltration recall ≈0.29 at high
intensity is a genuine, unresolved weak point (not tuned away); the trust-only ablation variant
trades precision for a longer post-incident alert window by design; the real-network switch/AP
adapters are honest `UNSUPPORTED` stubs, not verified against physical hardware.
