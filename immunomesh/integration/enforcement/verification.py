"""Independent verification (Section 16): 'Never report successful isolation merely because an
API call returned without an exception.' Calls the adapter's own verify method and nothing else —
verification never infers success from the absence of an error."""
from __future__ import annotations
from immunomesh.integration.status import OpStatus
from immunomesh.integration.switch.base import ActionResult, SwitchAdapter


def verify(adapter: SwitchAdapter, mac_or_port: str) -> ActionResult:
    result = adapter.verify_isolation(mac_or_port)
    if result.status not in (OpStatus.VERIFIED, OpStatus.FAILED, OpStatus.UNSUPPORTED):
        # An adapter that returns anything else is behaving incorrectly — never let that read as success.
        return ActionResult(OpStatus.FAILED, f"adapter returned an unexpected verification status: {result.status}")
    return result
