"""CI-safe: builds synthetic Ethernet frames by hand, no real socket/root needed (Section 19/30)."""
import struct, time
import pandas as pd
from immunomesh.integration.capture.pcap import parse_ethernet_ipv4
from immunomesh.integration.capture.flow import FlowAggregator, is_private, NormalizedFlow
from immunomesh.schema import RAW_COLUMNS


def eth_ipv4_tcp(src="192.168.1.10", dst="93.184.216.34", sport=51000, dport=443, flags=0x02, payload=b"x"*10):
    def ip4(s): return bytes(int(o) for o in s.split("."))
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, 5 << 4, flags, 65535, 0, 0) + payload
    total_len = 20 + len(tcp)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total_len, 0, 0, 64, 6, 0, ip4(src), ip4(dst))
    eth = b"\x00" * 12 + struct.pack("!H", 0x0800)
    return eth + ip_hdr + tcp


def eth_ipv4_udp(src="192.168.1.10", dst="8.8.8.8", sport=51000, dport=53, payload=b"dns"):
    def ip4(s): return bytes(int(o) for o in s.split("."))
    udp = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    total_len = 20 + len(udp)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total_len, 0, 0, 64, 17, 0, ip4(src), ip4(dst))
    eth = b"\x00" * 12 + struct.pack("!H", 0x0800)
    return eth + ip_hdr + udp


def test_parse_ipv4_tcp():
    pkt = parse_ethernet_ipv4(eth_ipv4_tcp(), time.time())
    assert pkt is not None and pkt.protocol == "TCP" and pkt.dst_port == 443 and pkt.tcp_flags == 0x02


def test_parse_ipv4_udp():
    pkt = parse_ethernet_ipv4(eth_ipv4_udp(), time.time())
    assert pkt is not None and pkt.protocol == "UDP" and pkt.dst_port == 53


def test_parse_non_ipv4_returns_none():
    garbage = b"\x00" * 12 + struct.pack("!H", 0x86DD) + b"\x00" * 40  # IPv6 ethertype
    assert parse_ethernet_ipv4(garbage, time.time()) is None


def test_is_private():
    assert is_private("192.168.1.5") and is_private("10.0.0.1") and is_private("127.0.0.1")
    assert not is_private("8.8.8.8")


def test_flow_aggregation_bidirectional_and_failed_conn():
    agg = FlowAggregator(idle_timeout_s=1.0)
    t0 = time.time()
    agg.add(parse_ethernet_ipv4(eth_ipv4_tcp(sport=51000, dport=443, flags=0x02), t0))       # SYN, no ACK back
    flows = agg.expire(t0 + 2.0, force_all=True)
    assert len(flows) == 1 and flows[0].failed_conn == 1 and flows[0].direction == "outbound"

    agg2 = FlowAggregator(idle_timeout_s=1.0)
    agg2.add(parse_ethernet_ipv4(eth_ipv4_tcp(sport=51000, dport=443, flags=0x02), t0))
    agg2.add(parse_ethernet_ipv4(eth_ipv4_tcp(src="93.184.216.34", dst="192.168.1.10", sport=443, dport=51000, flags=0x12), t0 + 0.01))
    flows = agg2.expire(t0 + 2.0, force_all=True)
    assert len(flows) == 1 and flows[0].failed_conn == 0 and flows[0].packet_count == 2


def test_flow_expiry_respects_idle_timeout():
    agg = FlowAggregator(idle_timeout_s=5.0)
    t0 = time.time()
    agg.add(parse_ethernet_ipv4(eth_ipv4_udp(), t0))
    assert agg.expire(t0 + 1.0) == [] and agg.active_count() == 1
    assert len(agg.expire(t0 + 10.0)) == 1 and agg.active_count() == 0


def test_normalized_flow_matches_raw_columns_schema():
    f = NormalizedFlow(time.time(), "192.168.1.10", "8.8.8.8", "UDP", 51000, 53, 4, 300, 0.2, 0, "outbound")
    row = f.to_schema_row(device_type="unknown")
    assert set(row) == set(RAW_COLUMNS)
    df = pd.DataFrame([row], columns=RAW_COLUMNS)
    assert len(df) == 1 and df.iloc[0]["label"] == -1
