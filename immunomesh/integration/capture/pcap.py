"""Pure-stdlib Ethernet/IPv4/TCP/UDP header parsing (Section 5). No scapy dependency, so the
edge runtime has no extra install burden on a Raspberry Pi. Parses only what ImmunoMesh's flow
schema needs; anything else (IPv6, VLAN tags, non-IP ethertypes) is reported as unparsed rather
than guessed at.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass

ETH_P_IP = 0x0800
ETH_HLEN = 14


@dataclass(frozen=True)
class ParsedPacket:
    timestamp: float
    src_ip: str
    dst_ip: str
    protocol: str          # "TCP" | "UDP" | "ICMP"
    src_port: int | None
    dst_port: int | None
    length: int
    tcp_flags: int | None  # raw TCP flags byte, or None for non-TCP


def _ipv4_to_str(b: bytes) -> str:
    return ".".join(str(x) for x in b)


def parse_ethernet_ipv4(raw: bytes, timestamp: float) -> ParsedPacket | None:
    """Parse one raw Ethernet frame captured via AF_PACKET. Returns None if it isn't an IPv4
    packet carrying TCP/UDP/ICMP (anything else is out of scope for the existing flow schema)."""
    if len(raw) < ETH_HLEN + 20:
        return None
    eth_type = struct.unpack("!H", raw[12:14])[0]
    if eth_type != ETH_P_IP:
        return None
    ip = raw[ETH_HLEN:]
    ver_ihl = ip[0]
    if ver_ihl >> 4 != 4:
        return None
    ihl = (ver_ihl & 0x0F) * 4
    if len(ip) < ihl:
        return None
    total_len = struct.unpack("!H", ip[2:4])[0]
    proto_num = ip[9]
    src_ip = _ipv4_to_str(ip[12:16])
    dst_ip = _ipv4_to_str(ip[16:20])
    payload = ip[ihl:]
    if proto_num == 6 and len(payload) >= 14:  # TCP
        sport, dport = struct.unpack("!HH", payload[0:4])
        flags = payload[13]
        return ParsedPacket(timestamp, src_ip, dst_ip, "TCP", sport, dport, total_len, flags)
    if proto_num == 17 and len(payload) >= 4:  # UDP
        sport, dport = struct.unpack("!HH", payload[0:4])
        return ParsedPacket(timestamp, src_ip, dst_ip, "UDP", sport, dport, total_len, None)
    if proto_num == 1:  # ICMP
        return ParsedPacket(timestamp, src_ip, dst_ip, "ICMP", None, None, total_len, None)
    return None  # other IP protocol (e.g. ESP, GRE, IGMP) — out of scope, not silently guessed
