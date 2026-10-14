"""Remaining Section 19 categories: adapter capability detection (SNMP/SSH, honest UNSUPPORTED
without real hardware) and dashboard live-data loading (LiveRunData, not yet unit-tested)."""
import json
import pandas as pd
import pytest
from immunomesh.integration.switch.snmp import SNMPSwitchAdapter
from immunomesh.integration.switch.ssh import SSHSwitchAdapter
from immunomesh.integration.security.credentials import Credential
from immunomesh.integration.status import OpStatus, CapabilityStatus
from immunomesh.integration.dashboard_live import LiveRunData


def test_snmp_adapter_unsupported_without_host():
    a = SNMPSwitchAdapter(host=None)
    assert a.status() == OpStatus.UNSUPPORTED
    assert all(v in (CapabilityStatus.UNKNOWN, CapabilityStatus.UNSUPPORTED) for v in a.get_capabilities().values())
    assert a.isolate_device("x").status == OpStatus.UNSUPPORTED
    assert a.restore_device("x", None).status == OpStatus.UNSUPPORTED
    assert a.verify_isolation("x").status == OpStatus.UNSUPPORTED


def test_snmp_adapter_never_claims_live_even_with_host_configured():
    # No real device to connect to in this environment — must stay UNSUPPORTED, never LIVE.
    a = SNMPSwitchAdapter(host="192.0.2.99", community="public")
    assert a.status() == OpStatus.UNSUPPORTED


def test_ssh_adapter_unsupported_without_credential():
    a = SSHSwitchAdapter(host="192.0.2.99", credential=None)
    assert a.status() == OpStatus.UNSUPPORTED
    assert a.isolate_device("x").status == OpStatus.UNSUPPORTED


def test_ssh_adapter_unsupported_even_with_credential_but_no_real_switch():
    a = SSHSwitchAdapter(host="192.0.2.99", credential=Credential("admin", "x", source="env"))
    assert a.status() == OpStatus.UNSUPPORTED  # never LIVE without an actually verified connection


def test_live_run_data_loads_real_hil_output_if_present():
    import os
    if not os.path.isdir("results/hil"):
        pytest.skip("no HIL run present in this environment")
    ld = LiveRunData("results/hil")
    assert isinstance(ld.devices(), pd.DataFrame)
    assert isinstance(ld.alerts(), pd.DataFrame)
    h = ld.health()
    assert h["mode"] == "HIL_SELFTEST"


def test_live_run_data_handles_missing_directory_without_crashing(tmp_path):
    ld = LiveRunData(tmp_path / "nonexistent")
    assert ld.devices().empty and ld.alerts().empty and ld.performance().empty
    assert ld.health()["mode"] == "unknown"


def test_live_run_data_reads_devices_csv(tmp_path):
    d = tmp_path / "run"; d.mkdir()
    pd.DataFrame([{"ip": "192.168.1.5", "device_type": "camera"}]).to_csv(d / "devices.csv", index=False)
    (d / "run_manifest.json").write_text(json.dumps({"mode": "LIVE", "final_health": "healthy"}))
    ld = LiveRunData(d)
    assert len(ld.devices()) == 1 and ld.health()["mode"] == "LIVE"
