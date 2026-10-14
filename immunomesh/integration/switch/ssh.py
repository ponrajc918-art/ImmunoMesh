"""SSH switch adapter skeleton (Section 10). Lazy-imports `paramiko`; same UNSUPPORTED-by-default
honesty as snmp.py. Command templates come from vendor.py and are illustrative, not verified."""
from __future__ import annotations
from immunomesh.integration.network.capabilities import Capability, CapabilityReport
from immunomesh.integration.security.credentials import Credential
from immunomesh.integration.status import CapabilityStatus, OpStatus
from immunomesh.integration.switch.base import ActionResult, SwitchAdapter

try:
    import paramiko as _paramiko  # noqa: F401
    _HAVE_PARAMIKO = True
except ImportError:
    _HAVE_PARAMIKO = False


class SSHSwitchAdapter(SwitchAdapter):
    def __init__(self, host: str | None, credential: Credential | None, vendor_profile: str = "cisco_ios_like") -> None:
        self.host, self.credential, self.vendor_profile = host, credential, vendor_profile
        self._status = OpStatus.UNSUPPORTED
        if not _HAVE_PARAMIKO:
            self._detail = "paramiko not installed (see requirements-runtime.txt)"
        elif not host or not credential:
            self._detail = "no host/credential configured (set IMMUNOMESH_SWITCH_USERNAME/PASSWORD)"
        else:
            self._detail = "configured but not yet connected (no physical switch available to verify against)"

    def status(self) -> OpStatus:
        return self._status

    def get_devices(self) -> list[dict]:
        return []

    def get_port_status(self, port: str) -> dict:
        return {"port": port, "status": self._detail}

    def get_capabilities(self) -> CapabilityReport:
        return {c: CapabilityStatus.UNKNOWN for c in Capability}

    def isolate_device(self, mac_or_port: str) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)

    def restore_device(self, mac_or_port: str, previous_state: dict | None) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)

    def verify_isolation(self, mac_or_port: str) -> ActionResult:
        return ActionResult(OpStatus.UNSUPPORTED, self._detail)
