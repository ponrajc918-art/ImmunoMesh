# Troubleshooting

- **`doctor` shows capture_permission DEGRADED**: not running as root / no `CAP_NET_RAW`. Run
  with `sudo`, or `sudo setcap cap_net_raw+ep $(which python3)` for a non-root service user.
- **`capture`/`monitor` shows 0 packets despite real traffic**: check `--interface` matches the
  link actually carrying the traffic (`python -m immunomesh.cli status` lists the default);
  confirm `doctor`'s capture_permission check passes first.
- **Baseline never finishes (`BASELINE_COLLECTION` never transitions)**: flows only close after
  `idle_timeout_s` of inactivity (default = feature window + 5s ≈ 15s) — this is correct
  NetFlow-style behaviour, not a hang. Use `--idle-timeout` for a shorter demo value.
- **Every live flow reads as anomalous**: a very small baseline (a handful of flows, as in
  `results/hil/`) overfits the per-device baseline — every subsequent flow looks like a
  deviation. Collect a larger, more representative baseline window before trusting MONITORING
  output; this is a documented limitation, not a bug (see `docs/LIMITATIONS.md`).
- **`enforce` always refuses**: by design unless `config/live.yaml` has both
  `runtime.mode: enforce` and `enforcement.enabled: true`, and even then a real switch adapter
  must be configured — the shipped `dry_run` adapter never performs real actions.
