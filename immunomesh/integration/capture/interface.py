"""Network interface enumeration (Section 4/13), stdlib only (no netifaces dependency)."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InterfaceInfo:
    name: str
    is_up: bool
    rx_bytes: int
    tx_bytes: int


def list_interfaces() -> list[InterfaceInfo]:
    """Reads /sys/class/net (Linux). Returns [] on other platforms rather than guessing."""
    base = Path("/sys/class/net")
    if not base.exists():
        return []
    out = []
    for iface in sorted(p.name for p in base.iterdir()):
        try:
            state = (base / iface / "operstate").read_text().strip()
        except OSError:
            state = "unknown"
        rx = tx = 0
        try:
            rx = int((base / iface / "statistics" / "rx_bytes").read_text().strip())
            tx = int((base / iface / "statistics" / "tx_bytes").read_text().strip())
        except OSError:
            pass
        out.append(InterfaceInfo(iface, state in ("up", "unknown"), rx, tx))
    return out


def default_interface() -> str | None:
    """Best-effort default: first non-loopback interface that is up, else the first interface."""
    ifaces = list_interfaces()
    for i in ifaces:
        if i.name != "lo" and i.is_up:
            return i.name
    return ifaces[0].name if ifaces else None
