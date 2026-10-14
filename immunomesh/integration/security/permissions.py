"""Environment capability probes (Section 34: 'no fake hardware status'). Every check here
actually attempts the operation (or its safe read-only equivalent) rather than assuming."""
from __future__ import annotations
import os
import socket
from dataclasses import dataclass


@dataclass
class CapabilityCheck:
    name: str
    ok: bool
    detail: str


def check_root() -> CapabilityCheck:
    try:
        ok = hasattr(os, "geteuid") and os.geteuid() == 0
    except Exception as e:
        return CapabilityCheck("root", False, str(e))
    return CapabilityCheck("root", ok, "running as root" if ok else "not running as root (raw capture needs CAP_NET_RAW or root)")


def check_raw_socket() -> CapabilityCheck:
    """Check AF_PACKET support and permissions without crashing on other operating systems."""
    if not hasattr(socket, "AF_PACKET"):
        return CapabilityCheck(
            "raw_socket",
            False,
            "AF_PACKET raw sockets are Linux-specific and unavailable on this platform",
        )

    try:
        s = socket.socket(
            socket.AF_PACKET,
            socket.SOCK_RAW,
            socket.htons(0x0003),
        )
        s.close()
        return CapabilityCheck(
            "raw_socket",
            True,
            "AF_PACKET SOCK_RAW opened successfully",
        )
    except PermissionError as e:
        return CapabilityCheck("raw_socket", False, f"permission denied: {e}")
    except OSError as e:
        return CapabilityCheck(
            "raw_socket",
            False,
            f"unavailable on this platform: {e}",
        )

def check_proc_net_arp(path: str = "/proc/net/arp") -> CapabilityCheck:
    try:
        with open(path) as f:
            f.readline()
        return CapabilityCheck("proc_net_arp", True, f"{path} readable (Linux ARP table)")
    except FileNotFoundError:
        return CapabilityCheck("proc_net_arp", False, f"{path} not present (non-Linux, restricted container, or wrong path)")
    except PermissionError as e:
        return CapabilityCheck("proc_net_arp", False, str(e))
