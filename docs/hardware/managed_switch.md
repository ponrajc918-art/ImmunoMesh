# Managed switch integration

`switch/base.py` defines the interface (`get_devices`, `get_port_status`, `get_capabilities`,
`isolate_device`, `restore_device`, `verify_isolation`). Three adapters:

- `switch/dry_run.py` — **the only adapter guaranteed to exist.** Always available, only ever
  logs what it would do, status always `DRY_RUN`. Used automatically whenever `runtime.mode` is
  `observe_only` or `dry_run`.
- `switch/snmp.py` — lazy-imports `pysnmp`; reports `UNSUPPORTED` with an honest reason (package
  missing / no host configured / not yet connected) rather than ever claiming `LIVE` without a
  verified connection. **Not tested against a real switch — none was available.**
- `switch/ssh.py` — same honesty contract, lazy-imports `paramiko`, uses command templates from
  `switch/vendor.py` (documentation only, not validated against real hardware).

Capability discovery (VLAN/ACL/port-shutdown/MAC-isolation/port-mirroring) is reported as
`SUPPORTED`/`UNSUPPORTED`/`UNKNOWN` per `network/capabilities.py` — `UNKNOWN` whenever no real
device has actually been queried, never assumed `SUPPORTED`.

Before any real `isolate_device` call is trusted, test it against a lab switch you can recover
manually, and read `docs/hardware/enforcement.md` for the confirmation/verification/rollback
contract the executor enforces around it.
