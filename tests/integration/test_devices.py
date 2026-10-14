from immunomesh.integration.devices.classification import classify
from immunomesh.integration.devices.registry import DeviceRegistry
from immunomesh.integration.discovery.base import DiscoveredDevice

def test_classify_camera_and_plc_and_unknown():
    assert classify({554, 443}).device_type == "camera"
    assert classify({502}).device_type == "plc"
    assert classify({9999}).device_type == "unknown"
    assert classify(set()).confidence == 0.0

def test_registry_merges_discovery_and_flow(tmp_path):
    reg = DeviceRegistry(tmp_path / "devices.db")
    reg.observe_discovery(DiscoveredDevice(ip="192.168.1.10", mac="aa:bb:cc:dd:ee:ff", source="arp"))
    dev = reg.observe_flow("192.168.1.10", 554)
    assert dev.mac == "aa:bb:cc:dd:ee:ff" and dev.device_type == "camera"
    assert "arp" in dev.sources and "flow_observation" in dev.sources
    reg.persist()
    df = reg.as_dataframe()
    assert len(df) == 1 and df.iloc[0]["device_type"] == "camera"
