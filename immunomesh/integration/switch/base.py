"""Switch adapter interface (Section 10). Read-only first, then dry-run, then real enforcement —
never the reverse. Every method returns an explicit, honestly-determined status."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from immunomesh.integration.network.capabilities import CapabilityReport
from immunomesh.integration.status import OpStatus


@dataclass
class ActionResult:
    status: OpStatus
    detail: str
    previous_state: dict | None = None   # captured before an action, for rollback


class SwitchAdapter(ABC):
    @abstractmethod
    def status(self) -> OpStatus: ...

    @abstractmethod
    def get_devices(self) -> list[dict]: ...

    @abstractmethod
    def get_port_status(self, port: str) -> dict: ...

    @abstractmethod
    def get_capabilities(self) -> CapabilityReport: ...

    @abstractmethod
    def isolate_device(self, mac_or_port: str) -> ActionResult: ...

    @abstractmethod
    def restore_device(self, mac_or_port: str, previous_state: dict | None) -> ActionResult: ...

    @abstractmethod
    def verify_isolation(self, mac_or_port: str) -> ActionResult: ...
