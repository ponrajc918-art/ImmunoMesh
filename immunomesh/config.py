"""Typed configuration loading (YAML -> dataclasses)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "default.yaml"
ALL_ATTACKS = ["traffic_spike", "port_scan", "brute_force", "exfiltration", "protocol_irregularity"]


@dataclass
class SimulationConfig:
    n_cameras: int = 4
    n_sensors: int = 3
    n_plcs: int = 2
    train_duration_s: float = 1800
    eval_duration_s: float = 1800
    anomalous_device_count: int = 2
    windows_per_device: int = 2
    window_length_s: float = 60
    intensity: str = "high"
    attack_types: list[str] = field(default_factory=lambda: list(ALL_ATTACKS))
    missing_rate: float = 0.005
    duplicate_rate: float = 0.003
    invalid_rate: float = 0.002


@dataclass
class FeatureConfig:
    window_s: float = 10.0


@dataclass
class DetectorConfig:
    n_estimators: int = 200
    max_samples: Any = 256
    threshold_quantile: float = 0.99


@dataclass
class EvidenceConfig:
    top_k: int = 5                # top SHAP contributors examined per flagged flow
    z_threshold: float = 3.0      # |robust z| vs device-type baseline to count as a deviation
    min_strength: float = 0.3     # share of top-k contribution backed by deviations -> "corroborated"
    baseline_by_service: bool = False  # compare against (device_type, dst_port) baseline when available
    min_service_n: int = 30       # min training flows for a service-level baseline


@dataclass
class MeshConfig:
    """Phases 7-9: epoch-level trust, peer consensus and simulated response (see docs/METHODOLOGY.md)."""
    epoch_s: float = 10.0
    k_min: int = 2                # min flagged flows for an epoch to be suspicious
    a_min: float = 0.3            # min flagged fraction for an epoch to be suspicious
    # trust
    trust_init: float = 1.0
    lambda_pen: float = 0.35
    lambda_rec: float = 0.10
    history_window: int = 6
    gamma: float = 0.5
    alert_trust: float = 0.7
    t_high: float = 0.5
    t_quar: float = 0.3
    # consensus
    omega: float = 0.3            # weight of peer support in consensus score
    visibility: float = 0.5       # prob. a peer observes a given flow of another device
    consensus_min: float = 0.3    # consensus needed to allow quarantine (when consensus enabled)
    # response
    cooldown_epochs: int = 6
    clear_epochs: int = 3         # clean epochs to leave SUSPICIOUS
    recover_clean_epochs: int = 3 # clean monitored epochs (after cooldown) to start RECOVERING
    probation_epochs: int = 3     # clean epochs in RECOVERING to be RESTORED
    recover_trust: float = 0.5
    escalation_factor: int = 2
    max_cooldown_epochs: int = 24
    # ablation switches
    use_evidence: bool = True
    use_trust: bool = True
    use_consensus: bool = True
    use_response: bool = True


@dataclass
class Config:
    seed: int = 42
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    mesh: MeshConfig = field(default_factory=MeshConfig)

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        s = self.simulation
        if s.intensity not in ("low", "high"):
            raise ValueError("simulation.intensity must be 'low' or 'high'")
        bad = set(s.attack_types) - set(ALL_ATTACKS)
        if bad:
            raise ValueError(f"unknown attack types: {sorted(bad)}")
        if not 0 < self.detector.threshold_quantile < 1:
            raise ValueError("detector.threshold_quantile must be in (0, 1)")
        if s.anomalous_device_count > s.n_cameras + s.n_sensors + s.n_plcs:
            raise ValueError("anomalous_device_count exceeds number of devices")
        if s.windows_per_device * s.window_length_s > s.eval_duration_s:
            raise ValueError("attack windows do not fit in the evaluation period")
        m = self.mesh
        if not 0 < m.t_quar < m.t_high < m.alert_trust <= 1:
            raise ValueError("mesh thresholds must satisfy 0 < t_quar < t_high < alert_trust <= 1")
        if not 0 <= m.omega <= 1 or not 0 < m.visibility <= 1:
            raise ValueError("mesh.omega in [0,1] and mesh.visibility in (0,1]")


def from_dict(d: dict) -> Config:
    cfg = Config(
        seed=int(d.get("seed", 42)),
        simulation=SimulationConfig(**d.get("simulation", {})),
        features=FeatureConfig(**d.get("features", {})),
        detector=DetectorConfig(**d.get("detector", {})),
        evidence=EvidenceConfig(**d.get("evidence", {})),
        mesh=MeshConfig(**d.get("mesh", {})),
    )
    cfg.validate()
    return cfg


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> Config:
    """Load YAML config; `overrides` is a nested dict merged on top."""
    with open(path or DEFAULT_CONFIG) as fh:
        d = yaml.safe_load(fh) or {}
    for k, v in (overrides or {}).items():
        if isinstance(v, dict):
            d.setdefault(k, {}).update(v)
        else:
            d[k] = v
    return from_dict(d)
