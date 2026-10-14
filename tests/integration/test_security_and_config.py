"""Section 18 (credential security) and Section 19 (configuration validation)."""
import logging
import os
import pytest
from immunomesh.integration.security.credentials import load_credential, install_redaction, RedactingFilter
from immunomesh.integration.config import LiveConfig, load_live_config, RuntimeSection, EnforcementSection, SwitchSection


def test_credential_loads_from_env_and_never_bare_prints_password(monkeypatch):
    monkeypatch.setenv("IMMUNOMESH_SWITCH_USERNAME", "admin")
    monkeypatch.setenv("IMMUNOMESH_SWITCH_PASSWORD", "hunter2")
    cred = load_credential("SWITCH")
    assert cred.username == "admin" and cred.password == "hunter2"
    r = cred.redacted()
    assert r["password"] == "<redacted>" and "hunter2" not in str(r)


def test_credential_absent_returns_none(monkeypatch):
    monkeypatch.delenv("IMMUNOMESH_SWITCH_USERNAME", raising=False)
    monkeypatch.delenv("IMMUNOMESH_SWITCH_PASSWORD", raising=False)
    assert load_credential("SWITCH") is None


def test_logging_redacts_secrets(caplog):
    log = logging.getLogger("test.redaction")
    install_redaction(log)
    install_redaction(log)  # idempotent — must not double-install
    assert sum(isinstance(f, RedactingFilter) for f in log.filters) == 1
    with caplog.at_level(logging.INFO):
        log.info("connecting with password=hunter2 to switch")
    assert "hunter2" not in caplog.text
    assert "<redacted>" in caplog.text


def test_live_config_defaults_are_safe():
    cfg = LiveConfig()
    assert cfg.runtime.mode == "observe_only"
    assert cfg.enforcement.enabled is False
    cfg.validate()  # must not raise


def test_live_config_rejects_enforcement_without_enforce_mode():
    cfg = LiveConfig(runtime=RuntimeSection(mode="observe_only"), enforcement=EnforcementSection(enabled=True))
    with pytest.raises(ValueError):
        cfg.validate()


def test_live_config_rejects_bad_switch_adapter():
    cfg = LiveConfig(switch=SwitchSection(adapter="not_a_real_adapter"))
    with pytest.raises(ValueError):
        cfg.validate()


def test_live_config_rejects_bad_mode():
    cfg = LiveConfig(runtime=RuntimeSection(mode="super_enforce"))
    with pytest.raises(ValueError):
        cfg.validate()


def test_load_live_config_from_repo_default_is_observe_only():
    cfg = load_live_config()
    assert cfg.runtime.mode == "observe_only" and cfg.enforcement.enabled is False
