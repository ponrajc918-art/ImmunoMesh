# Security

- Credentials: only read from `IMMUNOMESH_<PREFIX>_USERNAME`/`_PASSWORD` environment variables
  (`security/credentials.py`), never hardcoded, never written to `config/live.yaml` or any
  `results/` file. `RedactingFilter` scrubs anything secret-shaped from every log line emitted by
  the integration layer (`tests/integration/test_security_and_config.py` verifies this).
- No sensitive identification numbers, account numbers, or real individuals' data are collected
  by discovery/classification — only IP/MAC/open-port observations needed for device typing.
- Enforcement requires explicit `confirmed=True` under `RuntimeMode.ENFORCE` —
  `executor.Executor` refuses otherwise (`test_enforce_requires_explicit_confirmation`).
- See `docs/hardware/enforcement.md` for the full authorize/execute/verify/rollback contract.

## Known security notes and limits of review
- `AnomalyDetector.load` uses `joblib.load`, which unpickles. **Only load detector files you created
  yourself**; a malicious `.joblib` can execute arbitrary code. No CLI command loads one, and the
  repository publishes none (`results/run_seed*/detector.joblib` is git-ignored).
- Commands that write a results directory (`cli demo --out`, the HIL self-test) refuse to touch a
  non-empty directory that is not a previous run of the same command, and delete only files they
  generate (`immunomesh/safe_io.py`; regression tests in `tests/test_safe_output_dir.py`).
  An earlier version ran `shutil.rmtree` on the user-supplied path.
- Packet capture needs root or `CAP_NET_RAW`. The systemd unit runs as root for simplicity; a
  dedicated user with only `CAP_NET_RAW` would be safer and is untested.
- Enforcement defaults to `observe_only` and cannot be enabled through config without both
  `runtime.mode: enforce` and `enforcement.enabled: true`; nothing in `monitor`/`edge` calls the
  executor at all. Real switch adapters (SNMP/SSH) are unverified skeletons.
- The v1.0.0 review was a manual code read plus pattern searches for credentials, `subprocess`, `eval`,
  deserialisation, deletion and sockets, and a search for non-example IP addresses. It was **not** a
  comprehensive security audit: no dependency-vulnerability scan, no static analyser, no fuzzing of the
  packet parser, and no review of third-party package code.
