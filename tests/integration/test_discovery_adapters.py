"""Discovery adapters, capture failure, and interface failure (Section 19 — all previously only
exercised indirectly)."""
import socket
from immunomesh.integration.capture.raw_socket import RawSocketCaptureAdapter
from immunomesh.integration.discovery.arp import ARPDiscovery
from immunomesh.integration.discovery.dhcp import observe, DHCP_SERVER_PORT, DHCP_CLIENT_PORT
from immunomesh.integration.capture.pcap import ParsedPacket
from immunomesh.integration.status import OpStatus

ARP_SAMPLE = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:ff     *        eth0
192.168.1.99     0x1         0x0         00:00:00:00:00:00     *        eth0
192.168.1.50     0x1         0x2         11:22:33:44:55:66     *        eth0
"""


def test_arp_discovery_reads_real_file_format(tmp_path):
    p = tmp_path / "arp"
    p.write_text(ARP_SAMPLE)
    d = ARPDiscovery(path=str(p))
    assert d.status() == OpStatus.LIVE
    found = d.discover()
    ips = {x.ip for x in found}
    assert ips == {"192.168.1.1", "192.168.1.50"}  # incomplete (flags 0x0) and all-zero MAC excluded


def test_arp_discovery_missing_file_reports_unsupported(tmp_path):
    d = ARPDiscovery(path=str(tmp_path / "does_not_exist"))
    assert d.status() == OpStatus.UNSUPPORTED
    assert d.discover() == []


def test_dhcp_observation_hints_from_client_traffic():
    pkt = ParsedPacket(0.0, "192.168.1.77", "255.255.255.255", "UDP", DHCP_CLIENT_PORT, DHCP_SERVER_PORT, 300, None)
    hint = observe(pkt)
    assert hint is not None and hint.ip == "192.168.1.77" and hint.source == "dhcp"


def test_dhcp_observation_ignores_non_dhcp_udp():
    pkt = ParsedPacket(0.0, "192.168.1.77", "8.8.8.8", "UDP", 51000, 53, 80, None)
    assert observe(pkt) is None


def test_capture_adapter_invalid_interface_reports_unsupported_not_crash():
    cap = RawSocketCaptureAdapter("this-interface-does-not-exist-9999", timeout_s=0.1)
    assert cap.status() == OpStatus.UNSUPPORTED
    assert cap.error() is not None
    assert cap.recv_one() is None            # must not raise
    assert list(cap.packets()) == []          # generator must end cleanly, not hang or raise
    cap.stop()                                # must be safe to call even though nothing opened


def test_capture_adapter_recv_one_safe_before_any_bind_failure_is_handled():
    # A second, independent failure path: interface name valid-looking but non-existent.
    cap = RawSocketCaptureAdapter("eth99", timeout_s=0.1)
    assert cap.status() == OpStatus.UNSUPPORTED
    cap.stop()
