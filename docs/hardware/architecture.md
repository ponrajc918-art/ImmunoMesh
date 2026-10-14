# Real-network integration architecture

Adds a capture/discovery/enforcement layer around the frozen Phase 1-10 simulation core
(`immunomesh/{simulation,preprocessing,features,detection,evidence,trust,consensus,response,
storage,mesh}` — untouched by this layer; see `docs/PHASE_STATUS.md`).

```
real capture (capture/raw_socket.py, stdlib AF_PACKET — no scapy)
        |
flow aggregation (capture/flow.py) -- documented mapping to schema.RAW_COLUMNS
        |
device registry/classification (devices/)         discovery (discovery/: ARP passive, mDNS
        |                                          best-effort, DHCP-observation)
runtime/live.py: BASELINE_COLLECTION -> MONITORING
  - fit_baseline(cfg, train_raw=<live flows>)   <- EXISTING Phase 1-5 code, unmodified
  - evaluate_scenario(cfg, ctx, <live flows>)   <- EXISTING Phase 1-5 code, unmodified
  - EvidenceGenerator, TrustEngine              <- EXISTING Phase 6-7 code, unmodified
        |
runtime/supervisor.py (health-state wrapper: healthy/degraded/failed/recovering)
        |
enforcement/ (policy -> executor -> verification, gated by RuntimeMode; switch/dry_run.py is
the only adapter guaranteed to exist; switch/snmp.py, switch/ssh.py are lazy-import skeletons,
switch/vendor.py is documentation only — none are verified against real hardware)
        |
storage.audit.AuditStore (existing Phase 9 code, unmodified) + devices/registry.py (new)
        |
dashboard "Live Network" tab (immunomesh/dashboard/app.py, 8th tab) — reads results/live or
results/hil only, never simulation output
```

Config is intentionally split: `immunomesh.config.Config` (frozen, simulation) vs
`immunomesh.integration.config.LiveConfig` (`config/live.yaml`, this layer) — they are never
merged, so nothing here can perturb the regression-tested Phase 1-5 baseline.
