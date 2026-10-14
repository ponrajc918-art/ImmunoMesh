"""Access-point adapter interface (Section 4). No concrete implementation ships in this project —
no AP hardware or vendor API was available to build and verify one against. Present as an honest
interface + capability-detection stub, per Section 4: 'provide concrete implementations only
where technically supported.'"""
from __future__ import annotations
from abc import ABC, abstractmethod
from immunomesh.integration.network.capabilities import CapabilityReport, unknown_report
from immunomesh.integration.status import OpStatus


class AccessPointAdapter(ABC):
    @abstractmethod
    def status(self) -> OpStatus: ...
    @abstractmethod
    def get_capabilities(self) -> CapabilityReport: ...
    @abstractmethod
    def disconnect_client(self, mac: str) -> OpStatus: ...


class UnconfiguredAccessPointAdapter(AccessPointAdapter):
    """The only AP adapter this project ships. Always reports UNSUPPORTED, honestly."""
    def status(self) -> OpStatus:
        return OpStatus.UNSUPPORTED
    def get_capabilities(self) -> CapabilityReport:
        return unknown_report()
    def disconnect_client(self, mac: str) -> OpStatus:
        return OpStatus.UNSUPPORTED
