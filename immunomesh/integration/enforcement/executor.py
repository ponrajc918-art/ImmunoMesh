"""Enforcement executor (Section 16/17): gates every action by RuntimeMode, and only ever routes
to a real adapter under ENFORCE with explicit confirmation. Records the full stage sequence
(REQUESTED -> ... -> VERIFIED/FAILED/ROLLED_BACK) for audit (Section 16)."""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from immunomesh.integration.enforcement.policy import ProposedAction
from immunomesh.integration.security.credentials import install_redaction
from immunomesh.integration.status import EnforcementStage, OpStatus, RuntimeMode
from immunomesh.integration.switch.base import SwitchAdapter

log = logging.getLogger("immunomesh.integration.enforcement")
install_redaction(log)


@dataclass
class EnforcementRecord:
    ts: float
    device: str
    action: str
    mode: RuntimeMode
    stage: EnforcementStage
    detail: str
    previous_state: dict | None = None


class Executor:
    def __init__(self, mode: RuntimeMode, adapter: SwitchAdapter, dry_run_adapter: SwitchAdapter,
                require_confirmation: bool = True) -> None:
        self.mode, self.adapter, self.dry_run_adapter = mode, adapter, dry_run_adapter
        self.require_confirmation = require_confirmation
        self.records: list[EnforcementRecord] = []
        self._rollback_state: dict[str, dict | None] = {}

    def _log(self, device, action, stage, detail, previous_state=None) -> EnforcementRecord:
        rec = EnforcementRecord(time.time(), device, action, self.mode, stage, detail, previous_state)
        self.records.append(rec)
        log.info("[%s] %s %s -> %s: %s", self.mode.value, device, action, stage.value, detail)
        return rec

    def execute(self, proposed: ProposedAction, confirmed: bool = False) -> EnforcementRecord:
        if proposed.action == "none":
            return self._log(proposed.device, "none", EnforcementStage.EXECUTED, proposed.reason)

        self._log(proposed.device, proposed.action, EnforcementStage.REQUESTED, proposed.reason)

        if self.mode == RuntimeMode.OBSERVE_ONLY:
            return self._log(proposed.device, proposed.action, EnforcementStage.EXECUTED,
                             "OBSERVE_ONLY mode: action logged, nothing sent to any adapter")

        if self.mode == RuntimeMode.DRY_RUN:
            self._log(proposed.device, proposed.action, EnforcementStage.AUTHORIZED, "dry-run auto-authorized")
            if proposed.action == "isolate":
                r = self.dry_run_adapter.isolate_device(proposed.device)
            else:
                r = self.dry_run_adapter.restore_device(proposed.device, self._rollback_state.get(proposed.device))
            return self._log(proposed.device, proposed.action, EnforcementStage.EXECUTED, r.detail)

        # ENFORCE
        if self.require_confirmation and not confirmed:
            return self._log(proposed.device, proposed.action, EnforcementStage.FAILED,
                             "ENFORCE mode requires explicit confirmation (confirmed=True) — refusing to act silently")
        self._log(proposed.device, proposed.action, EnforcementStage.AUTHORIZED, "explicitly confirmed by operator")
        self._log(proposed.device, proposed.action, EnforcementStage.EXECUTING, f"calling {type(self.adapter).__name__}")
        if proposed.action == "isolate":
            r = self.adapter.isolate_device(proposed.device)
            if r.status == OpStatus.LIVE:
                self._rollback_state[proposed.device] = r.previous_state
        else:
            r = self.adapter.restore_device(proposed.device, self._rollback_state.get(proposed.device))

        if r.status != OpStatus.LIVE:
            return self._log(proposed.device, proposed.action, EnforcementStage.FAILED, r.detail)
        self._log(proposed.device, proposed.action, EnforcementStage.EXECUTED, r.detail)

        v = self.adapter.verify_isolation(proposed.device) if proposed.action == "isolate" else r
        stage = EnforcementStage.VERIFIED if v.status == OpStatus.VERIFIED else EnforcementStage.FAILED
        if stage == EnforcementStage.FAILED:
            rb = self.rollback(proposed)
            log.warning("verification failed for %s; rollback stage=%s", proposed.device, rb.stage.value)
            return rb
        return self._log(proposed.device, proposed.action, stage, v.detail)

    def rollback(self, proposed: ProposedAction) -> EnforcementRecord:
        prev = self._rollback_state.get(proposed.device)
        if not hasattr(self.adapter, "restore_device"):
            return self._log(proposed.device, proposed.action, EnforcementStage.ROLLBACK_UNSUPPORTED,
                             "adapter has no restore path")
        r = self.adapter.restore_device(proposed.device, prev)
        stage = EnforcementStage.ROLLED_BACK if r.status in (OpStatus.LIVE, OpStatus.VERIFIED) else EnforcementStage.FAILED
        return self._log(proposed.device, proposed.action, stage, r.detail)
