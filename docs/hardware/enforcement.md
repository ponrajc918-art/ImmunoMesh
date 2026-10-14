# Enforcement

`enforcement/policy.py` maps the EXISTING Phase 9 response state (`HIGH_RISK`/`QUARANTINED`/etc,
unmodified) to a proposed `isolate`/`restore`/`none` action — no new detection logic.
`enforcement/executor.py` gates every action by `RuntimeMode`:

- `OBSERVE_ONLY`: logs the proposal, calls no adapter at all.
- `DRY_RUN`: calls `switch/dry_run.py` only — never touches a real adapter.
- `ENFORCE`: requires `confirmed=True` explicitly passed by the caller, or refuses
  (`EnforcementStage.FAILED`, never silently proceeds). On success it calls
  `verify_isolation()` — **never infers success from the absence of an exception**;
  a verification that returns anything other than `VERIFIED`/`FAILED`/`UNSUPPORTED` is itself
  treated as `FAILED` (`enforcement/verification.py`).

Every stage (`REQUESTED -> AUTHORIZED -> EXECUTING -> EXECUTED -> VERIFIED|FAILED ->
ROLLED_BACK|ROLLBACK_UNSUPPORTED`) is appended to `Executor.records` for audit. A failed
verification automatically triggers `rollback()`, which calls the adapter's `restore_device`
with the state captured before the action; if the adapter can't restore, the stage is
`ROLLBACK_UNSUPPORTED` — reported, never silently swallowed.

All of this is exercised in `tests/integration/test_enforcement.py` with a fake switch adapter
(no physical switch was available to verify a real adapter against — see
`docs/hardware/managed_switch.md`).
