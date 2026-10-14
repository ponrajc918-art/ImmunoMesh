"""Passive ARP-table discovery (Section 4) — reads the kernel's existing table, sends nothing."""
from __future__ import annotations
import logging
from immunomesh.integration.discovery.base import DiscoveryAdapter, DiscoveredDevice
from immunomesh.integration.security.permissions import check_proc_net_arp
from immunomesh.integration.status import OpStatus

log = logging.getLogger("immunomesh.integration.discovery.arp")
ARP_PATH = "/proc/net/arp"
FLAG_COMPLETE = "0x2"


class ARPDiscovery(DiscoveryAdapter):
    def __init__(self, path: str = ARP_PATH) -> None:
        self.path = path
        self._status = OpStatus.LIVE if check_proc_net_arp(path).ok else OpStatus.UNSUPPORTED

    def status(self) -> OpStatus:
        return self._status

    def discover(self) -> list[DiscoveredDevice]:
        if self._status is not OpStatus.LIVE:
            return []
        out = []
        try:
            with open(self.path) as f:
                next(f)  # header
                for line in f:
                    parts = line.split()
                    if len(parts) < 6:
                        continue
                    ip, _hwtype, flags, mac, _mask, _dev = parts[:6]
                    if flags != FLAG_COMPLETE or mac in ("00:00:00:00:00:00",):
                        continue
                    out.append(DiscoveredDevice(ip=ip, mac=mac, source="arp", confidence=0.7))
        except OSError as e:
            log.warning("ARP read failed: %s", e)
            self._status = OpStatus.FAILED
        return out
