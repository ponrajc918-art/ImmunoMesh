"""Reusable pieces for running the full ImmunoMesh pipeline on a scenario (used by experiments + dashboard)."""
from __future__ import annotations
import dataclasses, time
from dataclasses import dataclass
import numpy as np
import pandas as pd
from immunomesh.config import Config, MeshConfig
from immunomesh.pipeline import fit_baseline, evaluate_scenario, TrainedContext
from immunomesh.simulation.traffic import generate_traffic, build_devices
from immunomesh.evidence.explainer import EvidenceGenerator
from immunomesh.consensus.peers import PeerObservers, build_observations
from immunomesh.mesh.engine import flow_arrays, run_mesh, n_epochs_for
from immunomesh.evaluation.metrics import detection_metrics
from immunomesh.evaluation.mesh_metrics import epoch_metrics, window_metrics, response_metrics


@dataclass
class SeedContext:
    cfg: Config
    ctx: TrainedContext
    evgen: EvidenceGenerator
    peers: PeerObservers
    devices: list[str]
    train_scores: np.ndarray


@dataclass
class ScenarioData:
    cfg: Config
    ev: dict
    evidence: pd.DataFrame
    peer_flags: np.ndarray
    shap_C: pd.DataFrame


def prepare_seed(cfg: Config) -> SeedContext:
    ctx = fit_baseline(cfg)
    devices = [d for d, _ in build_devices(cfg.simulation)]
    evgen = EvidenceGenerator(ctx.det, cfg.evidence).fit(ctx.train_f)
    peers = PeerObservers(cfg, devices).fit(ctx.Xtr)
    return SeedContext(cfg, ctx, evgen, peers, devices, ctx.det.score(ctx.Xtr))


def prepare_scenario(sc: SeedContext, sim_overrides: dict | None = None, threshold: float | None = None,
                     eval_seed: int | None = None, with_anomalies: bool = True) -> ScenarioData:
    sim = dataclasses.replace(sc.cfg.simulation, **(sim_overrides or {}))
    cfg = dataclasses.replace(sc.cfg, simulation=sim)
    raw = generate_traffic(sim, seed=(sc.cfg.seed + 1) if eval_seed is None else eval_seed, with_anomalies=with_anomalies)
    ev = evaluate_scenario(cfg, sc.ctx, raw, threshold=threshold)
    E, C = sc.evgen.explain(ev["eval_f"], ev["Xev"], ev["pred"])
    return ScenarioData(cfg, ev, E, sc.peers.flags(ev["Xev"]), C)


def run_variant(sc: SeedContext, sd: ScenarioData, mesh_overrides: dict | None = None) -> dict:
    """Run trust/consensus/response for one component configuration on prepared scenario data."""
    mesh = dataclasses.replace(sd.cfg.mesh, **(mesh_overrides or {}))
    cfg = dataclasses.replace(sd.cfg, mesh=mesh)
    E = mesh.epoch_s
    T = n_epochs_for(cfg.simulation.eval_duration_s, E)
    fl = flow_arrays(sd.ev["eval_f"], sd.ev["pred"], sd.evidence, sc.devices, E, T)
    peer_obs = None
    if mesh.use_consensus:
        peer_obs = build_observations(sd.peer_flags, fl["dev"], fl["epoch"], len(sc.devices), T, mesh.visibility, cfg.seed)
    t0 = time.perf_counter()
    res = run_mesh(cfg, sc.devices, fl, sd.ev["windows"], T, peer_obs)
    res["wall_s"] = time.perf_counter() - t0
    ep = res["epochs"]
    m = {}
    attacked = set(sd.ev["windows"].keys())
    m.update(epoch_metrics(ep, E, "alert", attacked))
    m.update(window_metrics(ep, sd.ev["windows"], E))
    if mesh.use_response:
        m.update({f"strict_{k}": v for k, v in epoch_metrics(ep, E, "alert_strict", attacked).items()})
        m.update(response_metrics(ep, res["events"], sd.ev["windows"], E))
    if mesh.use_consensus:
        m["mean_consensus_agreement"] = float(ep["agreement"].mean(skipna=True))
    m["mean_decision_ms"] = res["timing"]["mean_decision_ms"]
    res["metrics"] = m
    res["cfg"] = cfg
    return res


ABLATION = {
    "A0_anomaly_only": dict(use_evidence=False, use_trust=False, use_consensus=False, use_response=False),
    "A1_plus_evidence": dict(use_evidence=True, use_trust=False, use_consensus=False, use_response=False),
    "A2_plus_trust": dict(use_evidence=True, use_trust=True, use_consensus=False, use_response=False),
    "A3_plus_consensus": dict(use_evidence=True, use_trust=True, use_consensus=True, use_response=False),
    "A4_full_system": dict(use_evidence=True, use_trust=True, use_consensus=True, use_response=True),
}


def rethreshold(sc: SeedContext, sd: ScenarioData, quantile: float) -> ScenarioData:
    """Same scenario data, decision threshold = `quantile` of training scores (peers follow the same quantile)."""
    thr = float(np.quantile(sc.train_scores, quantile))
    ev = dict(sd.ev)
    pred = sc.ctx.det.predict(ev["Xev"], meta=ev["eval_f"], threshold=thr)
    pred["label"] = ev["eval_f"]["label"].to_numpy(); pred["attack_type"] = ev["eval_f"]["attack_type"].to_numpy()
    ev["pred"] = pred
    E, C = sc.evgen.explain(ev["eval_f"], ev["Xev"], pred)
    return ScenarioData(sd.cfg, ev, E, sc.peers.flags(ev["Xev"], quantile=quantile), C)
