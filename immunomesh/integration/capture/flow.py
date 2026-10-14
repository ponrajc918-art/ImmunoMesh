"""Bidirectional flow aggregation (Section 6) + the explicit real->ImmunoMesh feature mapping.

FLOW-TO-SCHEMA MAPPING (documented per Section 6 — keep this in sync with schema.RAW_COLUMNS):
  real flow field                    -> immunomesh.schema.RAW_COLUMNS field
  ---------------------------------------------------------------------------
  flow start time                    -> timestamp
  the LAN-side endpoint's identifier -> src_id   (IP address string; device registry may later
                                                   attach a friendlier label, see devices/identity.py)
  the other endpoint's identifier    -> dst_id   (IP address string)
  device_type                        -> device_type   (from devices/classification.py; "unknown"
                                                         if unclassified — an out-of-vocabulary
                                                         value for the existing one-hot encoder,
                                                         which degrades gracefully: see
                                                         docs/hardware/packet_capture.md)
  protocol (TCP/UDP/ICMP)            -> protocol      (anything else is out of scope, see pcap.py)
  LAN-side port                      -> src_port
  far-side port                      -> dst_port
  packets_forward + packets_backward -> packet_count
  bytes_forward + bytes_backward     -> byte_count
  end_time - start_time (floor 1e-3) -> duration_s
  1 if any TCP flow saw SYN but never a matching ACK from the far side, else 0
                                      -> failed_conn
  "outbound" if LAN-side is RFC1918/loopback and far side is not (or vice-versa -> "inbound");
  both private -> "outbound" by convention                                -> direction
  not available for live traffic (no ground truth)  -> label = -1, attack_type = "unknown"
"""
from __future__ import annotations
import ipaddress
import logging
from dataclasses import dataclass, field
from immunomesh.integration.capture.pcap import ParsedPacket
from immunomesh.schema import RAW_COLUMNS

log = logging.getLogger("immunomesh.integration.flow")
TCP_SYN, TCP_ACK = 0x02, 0x10


def is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return False


def _lan_side(pkt: ParsedPacket) -> tuple[str, str, bool]:
    """Returns (lan_ip, far_ip, src_is_lan) — which endpoint is treated as the monitored device."""
    src_p, dst_p = is_private(pkt.src_ip), is_private(pkt.dst_ip)
    if src_p and not dst_p:
        return pkt.src_ip, pkt.dst_ip, True
    if dst_p and not src_p:
        return pkt.dst_ip, pkt.src_ip, False
    return pkt.src_ip, pkt.dst_ip, True  # both private (or both public): convention, documented above


@dataclass
class _FlowState:
    key: tuple
    start: float
    end: float
    lan_ip: str
    far_ip: str
    protocol: str
    lan_port: int | None
    far_port: int | None
    packets: int = 0
    bytes_: int = 0
    saw_syn: bool = False
    saw_ack_from_far: bool = False


@dataclass
class NormalizedFlow:
    timestamp: float
    src_id: str
    dst_id: str
    protocol: str
    src_port: int | None
    dst_port: int | None
    packet_count: int
    byte_count: int
    duration_s: float
    failed_conn: int
    direction: str

    def to_schema_row(self, device_type: str = "unknown") -> dict:
        row = {
            "timestamp": self.timestamp, "src_id": self.src_id, "dst_id": self.dst_id,
            "device_type": device_type, "protocol": self.protocol,
            "src_port": self.src_port or 0, "dst_port": self.dst_port or 0,
            "packet_count": max(self.packet_count, 1), "byte_count": max(self.byte_count, 40),
            "duration_s": max(self.duration_s, 1e-3), "failed_conn": self.failed_conn,
            "direction": self.direction, "label": -1, "attack_type": "unknown",
        }
        assert set(row) == set(RAW_COLUMNS), "flow-to-schema mapping drifted from schema.RAW_COLUMNS"
        return row


class FlowAggregator:
    """Session-aware flow table with idle-timeout expiry. Not thread-safe; call from one thread."""
    def __init__(self, idle_timeout_s: float = 15.0) -> None:
        self.idle_timeout_s = idle_timeout_s
        self._flows: dict[tuple, _FlowState] = {}

    def _key(self, pkt: ParsedPacket) -> tuple:
        lan_ip, far_ip, src_is_lan = _lan_side(pkt)
        lan_port = pkt.src_port if src_is_lan else pkt.dst_port
        far_port = pkt.dst_port if src_is_lan else pkt.src_port
        return (lan_ip, far_ip, pkt.protocol, lan_port, far_port)

    def add(self, pkt: ParsedPacket) -> None:
        key = self._key(pkt)
        lan_ip, far_ip, src_is_lan = _lan_side(pkt)
        lan_port = pkt.src_port if src_is_lan else pkt.dst_port
        far_port = pkt.dst_port if src_is_lan else pkt.src_port
        st = self._flows.get(key)
        if st is None:
            st = _FlowState(key, pkt.timestamp, pkt.timestamp, lan_ip, far_ip, pkt.protocol, lan_port, far_port)
            self._flows[key] = st
        st.end = max(st.end, pkt.timestamp)
        st.packets += 1
        st.bytes_ += pkt.length
        if pkt.protocol == "TCP" and pkt.tcp_flags is not None:
            if src_is_lan and (pkt.tcp_flags & TCP_SYN) and not (pkt.tcp_flags & TCP_ACK):
                st.saw_syn = True
            if (not src_is_lan) and (pkt.tcp_flags & TCP_ACK):
                st.saw_ack_from_far = True

    def expire(self, now: float, force_all: bool = False) -> list[NormalizedFlow]:
        """Close and return flows idle longer than idle_timeout_s (or every flow if force_all)."""
        done, keep = [], {}
        for key, st in self._flows.items():
            if force_all or (now - st.end) > self.idle_timeout_s:
                failed = int(st.protocol == "TCP" and st.saw_syn and not st.saw_ack_from_far)
                done.append(NormalizedFlow(
                    timestamp=st.start, src_id=st.lan_ip, dst_id=st.far_ip, protocol=st.protocol,
                    src_port=st.lan_port, dst_port=st.far_port, packet_count=st.packets, byte_count=st.bytes_,
                    duration_s=st.end - st.start, failed_conn=failed,
                    direction="outbound" if is_private(st.lan_ip) else "inbound"))
            else:
                keep[key] = st
        self._flows = keep
        return done

    def active_count(self) -> int:
        return len(self._flows)
