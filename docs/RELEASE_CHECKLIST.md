# Release checklist — v1.0.0-research

Status reflects what was **actually executed** in the v1.0.0 verification pass. `[ ]` = not done or
not verifiable by the reviewer; the reason is stated.

## Tests, CI and environment
- [x] `pytest -q` → **75 passed, 0 failed, 0 skipped**, run in four environments: root and
      unprivileged-with-raw-sockets-denied (system env); a venv from `requirements-dev.txt`
      (scikit-learn 1.9.1, numpy 2.5.4); a venv from `requirements-lock.txt` (scikit-learn 1.8.0, numpy 2.4.4).
- [x] CI defect found and fixed: `ci.yml` runs bare `pytest -q`, which failed collection (13 import
      errors) because the package was neither installed nor on `sys.path`. Fixed with `pythonpath = .`
      in `pytest.ini`; all CI steps (`compileall`, `pytest -q`, `cli --help`, `doctor`, `discover`)
      then passed locally with exit code 0.
- [ ] **CI passes on GitHub — NOT VERIFIED.** No GitHub Actions run has been observed. After pushing,
      check the Actions tab and record the run URL here.
- [x] `requirements.txt` → alias of `requirements-dev.txt`; `pip check` clean.
- [x] `requirements-lock.txt` pins all 58 packages in the dependency closure; a venv built from it
      matches the file exactly. (Earlier it pinned only 10 top-level packages.)
- [x] Dashboard: `AppTest` with a demo run and with a missing run directory (8 tabs, no exception), and
      a real `streamlit run` server started via `cli dashboard` (health endpoint `ok`, page HTTP 200).
      Not opened in a browser, so visual rendering of live charts was not inspected.

## Security and hygiene
- [x] Defect fixed: `cli demo --out DIR` ran `shutil.rmtree(DIR)` and deleted unrelated files
      (reproduced). Replaced by `immunomesh/safe_io.py`; 5 regression tests.
- [x] Pattern-based scan (credentials, private keys, `subprocess`, `eval`, `yaml.load`, deletion,
      sockets, non-example IPs): nothing found. **Not a comprehensive security audit** — see
      `docs/hardware/security.md` for what was not covered.
- [x] `joblib.load` risk documented; no detector file is published (`results/run_seed*/detector.joblib` is git-ignored).
- [x] `.gitignore` present; `LICENSE` (MIT) present.
- [ ] **Confirm the copyright holder in `LICENSE` ("Ponraj C") is the name you want public.**
- [ ] Decide whether `results/final/demo/audit.db` (≈220 KB, synthetic) and `results/hil/*.db`
      (local loopback data) should be published; they contain no credentials or personal data.
- [x] Removed references to private build prompts ("Section N"/"Rule N") from public docs and results.
      52 such comments remain in source code (cosmetic, not changed).

## Results and research integrity
- [x] 8 seeds (200–207) present; every (experiment, scenario) row has 8 seeds.
- [x] Headline table independently recomputed from the raw per-seed JSON; matches the CSV to 1e-16.
- [x] `run_manifest.json` records seeds, resolved config, scenario IDs, package versions, platform,
      timestamp and output paths.
- [x] Repeatability: seed 200 re-run from scratch in a fresh venv matched the stored checkpoint exactly
      (1,422 numeric cells, max difference 0.0). **Seeds 201–207 not re-run in the fresh environment**;
      this is repeatability, not independent replication.
- [x] Report presentation fixed (no experimental number changed): E1 precision/recall/F1 shown as
      undefined instead of 0.0; per-attack table gains `n_seeds`, `min_recall`, `max_recall`;
      `RESULTS.md` explains flow-level vs epoch-level metrics. All other table cells verified unchanged.
- [x] Exfiltration weakness (recall 0.285 over 4 seeds) kept visible in tables, figure, README, limitations.
- [x] Trust/precision trade-off kept (epoch precision 0.855 → 0.354).
- [x] Model comparison reported as found: Isolation Forest is not the best detector; Isolation Forest was
      kept for the explainability design, not because it scores best.
- [x] A0 ≡ A1 reported (evidence layer changed no alert decisions).
- [x] HIL results contain no precision/recall; scope and the live-runtime limitations are stated.
- [x] README/METHODOLOGY separate simulation, loopback HIL and (not yet performed) physical hardware.
- [x] No "production-ready", "state-of-the-art", "real-world accuracy", "Raspberry Pi/camera/switch validated"
      claims in README or docs.
- [ ] Figure `per_attack_recall_E3.png` draws mean ± std whiskers that extend above 1.0 for a bounded
      metric (cosmetic; left unchanged).

## Publication (requires you)
- [ ] Repository root, branch and remote verified on your machine (`C:\immunomesh_project_1\immunomesh_project`).
- [ ] Release commit created and pushed; remote branch and commit hash recorded here: ________
- [ ] GitHub Actions run green: ________
- [ ] Final report/paper claims checked against `docs/EVIDENCE_SUMMARY.md`.

## Version
- [x] `immunomesh.__version__ == "1.0.0-research"`, README title and this file agree (no other version
      mechanism exists).
