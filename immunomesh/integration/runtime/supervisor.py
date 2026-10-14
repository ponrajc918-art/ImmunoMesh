"""Supervisor (Section 23): wraps LiveRuntime.run_once() so a single bad cycle (capture failure,
detector exception, disk-full audit write, etc.) degrades that subsystem instead of crashing the
whole edge process. Tracks health transitions explicitly (healthy/degraded/failed/recovering)."""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from immunomesh.integration.runtime.live import LiveRuntime
from immunomesh.integration.status import HealthState

log = logging.getLogger("immunomesh.integration.supervisor")


@dataclass
class SupervisorState:
    health: HealthState = HealthState.HEALTHY
    consecutive_failures: int = 0
    total_cycles: int = 0
    total_failures: int = 0
    last_error: str | None = None
    history: list[tuple[float, HealthState]] = field(default_factory=list)


class Supervisor:
    def __init__(self, runtime: LiveRuntime, fail_threshold: int = 3, recover_after: int = 2) -> None:
        self.runtime, self.fail_threshold, self.recover_after = runtime, fail_threshold, recover_after
        self.state = SupervisorState()
        self._recent_ok = 0

    def _transition(self, new: HealthState) -> None:
        if new != self.state.health:
            log.warning("health %s -> %s", self.state.health.value, new.value)
            self.state.history.append((time.time(), new))
        self.state.health = new

    def cycle(self) -> dict:
        self.state.total_cycles += 1
        try:
            result = self.runtime.run_once()
        except Exception as e:  # noqa: BLE001 — a supervisor's whole job is to not propagate this
            self.state.consecutive_failures += 1
            self.state.total_failures += 1
            self.state.last_error = f"{type(e).__name__}: {e}"
            self._recent_ok = 0
            log.error("run_once() failed (%d consecutive): %s", self.state.consecutive_failures, self.state.last_error)
            self._transition(HealthState.FAILED if self.state.consecutive_failures >= self.fail_threshold else HealthState.DEGRADED)
            return {"ok": False, "error": self.state.last_error, "health": self.state.health.value}

        self.state.consecutive_failures = 0
        self._recent_ok += 1
        if self.state.health != HealthState.HEALTHY and self._recent_ok >= self.recover_after:
            self._transition(HealthState.RECOVERING if self.state.health == HealthState.FAILED else HealthState.HEALTHY)
            if self.state.health == HealthState.RECOVERING and self._recent_ok >= self.recover_after * 2:
                self._transition(HealthState.HEALTHY)
        elif self.state.health == HealthState.HEALTHY:
            pass
        return {"ok": True, "health": self.state.health.value, **result}

    def run_forever(self, max_cycles: int | None = None, sleep_s: float = 1.0) -> None:
        n = 0
        while max_cycles is None or n < max_cycles:
            self.cycle()
            n += 1
            if max_cycles is None:
                time.sleep(sleep_s)
