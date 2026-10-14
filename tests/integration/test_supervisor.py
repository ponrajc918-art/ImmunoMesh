from immunomesh.integration.runtime.supervisor import Supervisor
from immunomesh.integration.status import HealthState


class _Boom:
    def __init__(self, fail_times): self.fail_times, self.i = fail_times, 0
    def run_once(self):
        self.i += 1
        if self.i in self.fail_times:
            raise RuntimeError("simulated capture failure")
        return {"state": "MONITORING", "new_flows": 0}


def test_supervisor_survives_and_records_failures():
    sup = Supervisor(_Boom(fail_times={2, 3, 4}), fail_threshold=3, recover_after=2)
    results = [sup.cycle() for _ in range(8)]
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False and results[2]["ok"] is False
    assert sup.state.total_failures == 3
    assert results[-1]["ok"] is True  # process kept running after failures, never crashed
