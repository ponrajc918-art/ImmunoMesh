"""Live-runtime configuration (Section 12), kept SEPARATE from immunomesh.config.Config so
the frozen simulation config (Phases 1-10) is never touched by this layer (Rule 1)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml
from immunomesh.integration.status import RuntimeMode

DEFAULT_LIVE_CONFIG = Path(__file__).resolve().parents[2] / "config" / "live.yaml"


@dataclass
class RuntimeSection:
    mode: str = "observe_only"   # observe_only | dry_run | enforce — never defaults to enforce


@dataclass
class CaptureSection:
    interface: str | None = None   # None => auto-detect at runtime (capture.interface.default_interface)
    enabled: bool = True
    idle_timeout_s: float = 15.0
    epoch_s: float = 10.0


@dataclass
class DiscoverySection:
    arp: bool = True
    dhcp: bool = True
    mdns: bool = True


@dataclass
class DevicesSection:
    auto_classification: bool = True


@dataclass
class SwitchSection:
    enabled: bool = False
    adapter: str = "none"   # none | dry_run | snmp | ssh


@dataclass
class EnforcementSection:
    enabled: bool = False
    require_confirmation: bool = True


@dataclass
class DashboardSection:
    enabled: bool = True


@dataclass
class LiveConfig:
    runtime: RuntimeSection = field(default_factory=RuntimeSection)
    capture: CaptureSection = field(default_factory=CaptureSection)
    discovery: DiscoverySection = field(default_factory=DiscoverySection)
    devices: DevicesSection = field(default_factory=DevicesSection)
    switch: SwitchSection = field(default_factory=SwitchSection)
    enforcement: EnforcementSection = field(default_factory=EnforcementSection)
    dashboard: DashboardSection = field(default_factory=DashboardSection)

    def runtime_mode(self) -> RuntimeMode:
        return RuntimeMode(self.runtime.mode.upper())

    def validate(self) -> None:
        if self.runtime.mode.upper() not in RuntimeMode.__members__:
            raise ValueError(f"runtime.mode must be one of {list(RuntimeMode.__members__)}")
        if self.enforcement.enabled and self.runtime.mode.lower() != "enforce":
            raise ValueError("enforcement.enabled=true requires runtime.mode: enforce (Rule 3: never silently enter ENFORCE mode)")
        if self.switch.adapter not in ("none", "dry_run", "snmp", "ssh"):
            raise ValueError(f"unknown switch.adapter: {self.switch.adapter}")

    def to_dict(self) -> dict:
        return asdict(self)


def load_live_config(path: str | Path | None = None) -> LiveConfig:
    p = Path(path or DEFAULT_LIVE_CONFIG)
    if not p.exists():
        cfg = LiveConfig()
    else:
        with open(p) as f:
            d = yaml.safe_load(f) or {}
        cfg = LiveConfig(
            runtime=RuntimeSection(**d.get("runtime", {})), capture=CaptureSection(**d.get("capture", {})),
            discovery=DiscoverySection(**d.get("discovery", {})), devices=DevicesSection(**d.get("devices", {})),
            switch=SwitchSection(**d.get("switch", {})), enforcement=EnforcementSection(**d.get("enforcement", {})),
            dashboard=DashboardSection(**d.get("dashboard", {})))
    cfg.validate()
    return cfg
