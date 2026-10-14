"""Passive DHCP observation (Section 4): reuses the existing packet-capture layer, filtering for
UDP ports 67/68, instead of a separate capture mechanism. No active DHCP requests are ever sent."""
from __future__ import annotations
from immunomesh.integration.capture.pcap import ParsedPacket
from immunomesh.integration.discovery.base import DiscoveredDevice

DHCP_SERVER_PORT, DHCP_CLIENT_PORT = 67, 68


def observe(pkt: ParsedPacket) -> DiscoveredDevice | None:
    """Call this on every parsed packet from a running capture; returns a DiscoveredDevice hint
    when the packet is DHCP client traffic, else None. This is a hint only (no options parsing —
    correctly parsing DHCP option 12/hostname would need the UDP payload, which callers can add
    by extending pcap.py if their deployment needs it)."""
    if pkt.protocol != "UDP":
        return None
    if pkt.dst_port == DHCP_SERVER_PORT or pkt.src_port == DHCP_CLIENT_PORT:
        return DiscoveredDevice(ip=pkt.src_ip, mac=None, source="dhcp", confidence=0.4)
    return None
