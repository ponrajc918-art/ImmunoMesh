"""Best-effort, honest hardware environment detection (Section 28) — every entry is either
DETECTED (with the evidence that triggered it) or NOT DETECTED. Nothing is assumed."""
from __future__ import annotations
from pathlib import Path


def detect_raspberry_pi() -> tuple[bool, str]:
    try:
        info = Path("/proc/cpuinfo").read_text()
    except OSError:
        return False, "/proc/cpuinfo unavailable"
    if "Raspberry Pi" in info or "BCM2" in info or "BCM27" in info:
        return True, "matched Raspberry Pi / BCM SoC string in /proc/cpuinfo"
    return False, "no Raspberry Pi / BCM SoC signature in /proc/cpuinfo (this is generic Linux hardware/container)"


def default_gateway() -> str | None:
    """Parses the kernel's routing table (Linux, /proc/net/route) for the default route. Read-only."""
    try:
        lines = Path("/proc/net/route").read_text().splitlines()[1:]
    except OSError:
        return None
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "00000000":
            gw_hex = parts[2]
            b = bytes.fromhex(gw_hex)
            return ".".join(str(x) for x in reversed(b))
    return None


def local_ip_for(interface: str | None = None) -> str | None:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # no packet is actually sent for UDP connect(); just picks a local route
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None
