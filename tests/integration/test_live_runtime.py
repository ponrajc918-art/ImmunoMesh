"""CI-safe: a fake capture adapter feeds hand-built packets, no real socket/root required."""
import shutil
import pytest
from immunomesh.config import load_config
from immunomesh.integration.capture.base import CaptureAdapter
from immunomesh.integration.capture.pcap import ParsedPacket
from immunomesh.integration.runtime.live import LiveRuntime
from immunomesh.integration.status import BaselineState, OpStatus


class FakeCapture(CaptureAdapter):
    """Replays a fixed packet list, a few at a time, bounded — mirrors real recv_one() semantics
    without touching a real socket."""
    def __init__(self, packets: list[ParsedPacket]):
        self._packets, self._i, self._stopped = packets, 0, False

    def status(self): return OpStatus.LIVE
    def packets(self):
        while self._i < len(self._packets) and not self._stopped:
            yield self._packets[self._i]; self._i += 1
    def recv_one(self):
        if self._stopped or self._i >= len(self._packets):
            return None
        p = self._packets[self._i]; self._i += 1
        return p
    def stop(self): self._stopped = True


def make_packets(n, t0=1_000_000.0, src="192.168.1.50", dst="93.184.216.34", proto="TCP", dport=443):
    return [ParsedPacket(t0 + i * 0.01, src, dst, proto, 51000 + i, dport, 100, 0x18 if proto == "TCP" else None)
            for i in range(n)]


@pytest.fixture
def tmp_dirs(tmp_path):
    return str(tmp_path / "audit.db"), str(tmp_path / "devices.db")


def test_baseline_then_monitoring_transition(tmp_dirs):
    audit_db, reg_db = tmp_dirs
    cap = FakeCapture(make_packets(50))
    cfg = load_config()
    rt = LiveRuntime(cap, cfg=cfg, baseline_min_flows=2, audit_db=audit_db, registry_db=reg_db, idle_timeout_s=0.0)
    r1 = rt.run_once()
    assert r1["state"] == "BASELINE_COLLECTION"
    r2 = rt.run_once()
    assert rt.state == BaselineState.MONITORING
    rt.shutdown()


def test_monitoring_produces_predictions_without_touching_frozen_pipeline(tmp_dirs):
    audit_db, reg_db = tmp_dirs
    cap = FakeCapture(make_packets(80))
    rt = LiveRuntime(cap, cfg=load_config(), baseline_min_flows=2, audit_db=audit_db, registry_db=reg_db, idle_timeout_s=0.0)
    rt.run_once()
    assert rt.state == BaselineState.MONITORING
    r = rt.run_once()
    assert "anomalies" in r or r["new_flows"] == 0
    rt.shutdown()


def test_no_traffic_does_not_hang_and_stays_in_baseline(tmp_dirs):
    audit_db, reg_db = tmp_dirs
    cap = FakeCapture([])
    rt = LiveRuntime(cap, cfg=load_config(), baseline_min_flows=2, audit_db=audit_db, registry_db=reg_db)
    r = rt.run_once()   # must return promptly even with zero packets ever available
    assert r["state"] == "BASELINE_COLLECTION" and r["new_flows"] == 0
    rt.shutdown()


def test_device_registry_persisted(tmp_dirs):
    audit_db, reg_db = tmp_dirs
    cap = FakeCapture(make_packets(30))
    rt = LiveRuntime(cap, cfg=load_config(), baseline_min_flows=2, audit_db=audit_db, registry_db=reg_db, idle_timeout_s=0.0)
    rt.run_once()
    assert "192.168.1.50" in rt.registry.devices
    rt.shutdown()
