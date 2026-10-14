"""SNMP switch adapter skeleton (Section 10). Lazy-imports `pysnmp`; UNSUPPORTED if the package
is absent or no target/credential is configured — never claims LIVE without a real, verified
connection."""
from __future__ import annotations
from immunomesh.integration.network.capabilities import Capability, CapabilityReport
from immunomesh.integration.security.credentials import Credential
from immunomesh.integration.status import CapabilityStatus, OpStatus
from immunomesh.integration.switch.base import ActionResult, SwitchAdapter

try:
    import pysnmp.hlapi as _snmp  # noqa: F401
    _HAVE_PYSNMP = True
except ImportError:
    _HAVE_PYSNMP = False


class SNMPSwitchAdapter(SwitchAdapter):
    def __init__(self, host: str | None, community: str | None = None, credential: Credential | None = None) -> None:
        self.host, self.community, self.credential = host, community, credential
        self._status = OpStatus.UNSUPPORTED
        self._detail = "pysnmp not installed (see requirements-runtime.txt)" if not _HAVE_PYSNMP else \
                       "no host configured" if not host else "not yet connected"

    def status(self) -> OpStatus:
        return self._status

    def get_devices(self) -> list[dict]:
        return []

    def get_port_status(self, port: str) -> dict:
        return {"port": port, "status": self._detail}

    def get_capabilities(self) -> CapabilityReport:
        # Read-only capability probing over SNMP is switch-specific (vendor MIBs); without a real
        # device to query, capabilities are UNKNOWN, never assumed SUPPORTED.
        return {c: CapabilityStatus.UNKNOWN if _HAVE_PYSNMP and self.host else CapabilityStatus.UNSUPPORTED
                for c in Capability}

    def isolate_device(self, mac_or_port: str) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)

    def restore_device(self, mac_or_port: str, previous_state: dict | None) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)

    def verify_isolation(self, mac_or_port: str) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)
