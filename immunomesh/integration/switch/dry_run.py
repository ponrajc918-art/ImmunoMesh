"""Always-available switch adapter that only ever logs intended actions (Section 3/10).

This is the adapter used whenever runtime mode is OBSERVE_ONLY or DRY_RUN, and the only adapter
guaranteed to exist regardless of what real hardware is configured."""
from __future__ import annotations
import logging
import time
from immunomesh.integration.network.capabilities import Capability, CapabilityReport
from immunomesh.integration.status import CapabilityStatus, OpStatus
from immunomesh.integration.switch.base import ActionResult, SwitchAdapter

log = logging.getLogger("immunomesh.integration.switch.dry_run")


class DryRunSwitchAdapter(SwitchAdapter):
    def __init__(self) -> None:
        self._log: list[dict] = []

    def status(self) -> OpStatus:
        return OpStatus.DRY_RUN

    def get_devices(self) -> list[dict]:
        return []  # no real device table without a real switch connection

    def get_port_status(self, port: str) -> dict:
        return {"port": port, "status": "UNKNOWN (dry-run adapter has no real switch connection)"}

    def get_capabilities(self) -> CapabilityReport:
        return {c: CapabilityStatus.UNKNOWN for c in Capability}

    def isolate_device(self, mac_or_port: str) -> ActionResult:
        entry = {"ts": time.time(), "action": "isolate_device", "target": mac_or_port}
        self._log.append(entry)
        log.info("DRY_RUN: would isolate %s (no real switch action taken)", mac_or_port)
        return ActionResult(OpStatus.DRY_RUN, f"would isolate {mac_or_port}; no real switch action taken")

    def restore_device(self, mac_or_port: str, previous_state: dict | None) -> ActionResult:
        entry = {"ts": time.time(), "action": "restore_device", "target": mac_or_port}
        self._log.append(entry)
        log.info("DRY_RUN: would restore %s", mac_or_port)
        return ActionResult(OpStatus.DRY_RUN, f"would restore {mac_or_port}; no real switch action taken")

    def verify_isolation(self, mac_or_port: str) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, "dry-run adapter cannot verify a real network state")

    def action_log(self) -> list[dict]:
        return list(self._log)
