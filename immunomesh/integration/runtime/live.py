"""Live/edge runtime (Section 11/21/22): ties real capture to the EXISTING Phase 1-9 pipeline,
unmodified (Rule 1/Section 7 — no second ML system).

State machine (Section 8): BASELINE_COLLECTION -> MONITORING (-> ALERT is a per-epoch label,
not a separate mode, mirroring how the Phase 9 response engine already reports per-device risk).

    real capture --> FlowAggregator --> schema rows --> (baseline: fit_baseline)
                                                      --> (monitoring: evaluate_scenario,
                                                           EvidenceGenerator, mesh epoch update,
                                                           AuditStore)  [[ALL EXISTING CODE]]
"""
from __future__ import annotations
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
import pandas as pd
from immunomesh.config import Config, load_config
from immunomesh.evidence.explainer import EvidenceGenerator
from immunomesh.integration.capture.base import CaptureAdapter
from immunomesh.integration.capture.flow import FlowAggregator
from immunomesh.integration.devices.registry import DeviceRegistry
from immunomesh.integration.status import BaselineState
from immunomesh.pipeline import TrainedContext, evaluate_scenario, fit_baseline
from immunomesh.schema import RAW_COLUMNS
from immunomesh.storage.audit import AuditStore
from immunomesh.trust.engine import TrustEngine

log = logging.getLogger("immunomesh.integration.runtime")


@dataclass
class RuntimeStats:
    packets_seen: int = 0
    flows_closed: int = 0
    epochs_processed: int = 0
    dropped_packets: int = 0
    last_batch_latency_ms: float = 0.0
    started_at: float = field(default_factory=time.time)


class LiveRuntime:
    """One monitored interface. `run_once()` processes whatever the capture adapter has produced
    since the last call — call it in a loop (see cli.py `edge`/`monitor`) or drive it from a test.
    """
    def __init__(self, capture: CaptureAdapter, cfg: Config | None = None,
                baseline_min_flows: int = 20, audit_db: str | None = "results/live/audit.db",
                registry_db: str | None = "results/live/devices.db", idle_timeout_s: float | None = None,
                queue_size: int = 20000) -> None:
        self.capture, self.cfg = capture, cfg or load_config()
        self.baseline_min_flows = baseline_min_flows
        self.agg = FlowAggregator(idle_timeout_s=idle_timeout_s if idle_timeout_s is not None else self.cfg.features.window_s + 5.0)
        # A dedicated background thread drains the capture adapter continuously (via its
        # streaming packets()) into a bounded queue, so the once-per-cycle processing cadence
        # below can never create a gap where real traffic is silently missed (Section 22). If
        # the queue fills (processing falls behind capture rate), the newest packet is dropped
        # and counted in self.stats.dropped_packets — never silently.
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._capture_stop = threading.Event()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self.registry = DeviceRegistry(registry_db)
        self.audit = AuditStore(audit_db) if audit_db else AuditStore()
        self.state = BaselineState.BASELINE_COLLECTION
        self.ctx: TrainedContext | None = None
        self.evgen: EvidenceGenerator | None = None
        self.trust: TrustEngine | None = None
        self.stats = RuntimeStats()
        self._baseline_rows: list[dict] = []
        self.experiment_id = f"live_{int(time.time())}"
        self.audit.register_experiment(self.experiment_id, seed=-1, config={"mode": "LIVE", "cfg": self.cfg.to_dict()})

    def _capture_loop(self) -> None:
        """Runs in its own thread for the runtime's lifetime; never shares the processing cadence
        of run_once(), so it never has a gap in which real traffic goes unobserved."""
        try:
            for pkt in self.capture.packets():
                if self._capture_stop.is_set():
                    return
                try:
                    self._queue.put_nowait(pkt)
                except queue.Full:
                    self.stats.dropped_packets += 1
        except Exception:
            log.exception("capture thread terminated unexpectedly")

    def _drain_packets(self, max_packets: int = 100_000) -> int:
        """Non-blocking: drains whatever the capture thread has already queued. Never waits for
        new packets, so a quiet link returns immediately with 0 — the capture thread, not this
        method, is what guarantees nothing is missed."""
        n = 0
        while n < max_packets:
            try:
                pkt = self._queue.get_nowait()
            except queue.Empty:
                break
            self.agg.add(pkt)
            self.registry.observe_flow(pkt.src_ip, pkt.src_port)
            n += 1
            self.stats.packets_seen += 1
        return n

    def _flow_rows(self) -> list[dict]:
        flows = self.agg.expire(now=time.time())
        self.stats.flows_closed += len(flows)
        rows = []
        for f in flows:
            dev = self.registry.devices.get(f.src_id)
            device_type = dev.device_type if dev else "unknown"
            rows.append(f.to_schema_row(device_type=device_type))
        return rows

    def run_once(self) -> dict:
        t0 = time.perf_counter()
        self._drain_packets()
        rows = self._flow_rows()
        result = {"state": self.state.value, "new_flows": len(rows), "packets_total": self.stats.packets_seen}

        if self.state == BaselineState.BASELINE_COLLECTION:
            self._baseline_rows.extend(rows)
            result["baseline_flows_collected"] = len(self._baseline_rows)
            if len(self._baseline_rows) >= self.baseline_min_flows:
                df = pd.DataFrame(self._baseline_rows, columns=RAW_COLUMNS)
                self.ctx = fit_baseline(self.cfg, train_raw=df)
                self.evgen = EvidenceGenerator(self.ctx.det, self.cfg.evidence).fit(self.ctx.train_f)
                self.trust = TrustEngine(self.cfg.mesh, list(self.registry.devices.keys()) or ["unknown"])
                self.state = BaselineState.MONITORING
                result["baseline_fit"] = True
                log.info("baseline fit on %d live flows; switching to MONITORING", len(df))
            self.stats.last_batch_latency_ms = (time.perf_counter() - t0) * 1000.0
            return result

        # MONITORING
        if rows:
            df = pd.DataFrame(rows, columns=RAW_COLUMNS)
            ev = evaluate_scenario(self.cfg, self.ctx, df)
            pred, feats = ev["pred"], ev["eval_f"]
            evidence, _ = self.evgen.explain(feats, ev["Xev"], pred)
            events = []
            for _, r in pred.iterrows():
                dev = str(r["device"])
                if dev not in self.trust.trust:
                    self.trust.trust[dev] = self.cfg.mesh.trust_init
                    from collections import deque
                    self.trust.hist[dev] = deque(maxlen=self.cfg.mesh.history_window)
                sev = float(r["confidence"]) if r["is_anomaly"] else 0.0
                T = self.trust.update(dev, sev)
                if r["is_anomaly"]:
                    events.append({"ts": float(r["timestamp"]), "device": dev, "event_type": "ANOMALY_DETECTED",
                                  "detection_score": float(r["anomaly_score"]), "trust": T,
                                  "risk_level": self.trust.risk_level(T),
                                  "evidence": None, "state_from": "MONITORING", "state_to": "MONITORING",
                                  "response": "OBSERVE_ONLY", "details": "LIVE traffic; detection + trust only. Consensus, the response state machine and the enforcement executor are NOT wired into this runtime"})
            if events:
                self.audit.log_events(self.experiment_id, events)
            result["anomalies"] = int(pred["is_anomaly"].sum())
            result["evidence_rows"] = len(evidence)
            self.stats.epochs_processed += 1
        self.stats.last_batch_latency_ms = (time.perf_counter() - t0) * 1000.0
        self.registry.persist()
        return result

    def shutdown(self) -> None:
        self._capture_stop.set()
        self.capture.stop()
        self._capture_thread.join(timeout=2.0)
        self.registry.persist()
        self.audit.close()
