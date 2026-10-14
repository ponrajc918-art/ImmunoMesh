from immunomesh.integration.enforcement.policy import propose
from immunomesh.integration.enforcement.executor import Executor
from immunomesh.integration.enforcement.verification import verify
from immunomesh.integration.status import OpStatus, RuntimeMode, EnforcementStage
from immunomesh.integration.switch.dry_run import DryRunSwitchAdapter
from immunomesh.integration.switch.base import ActionResult, SwitchAdapter


def test_policy_proposes_isolate_and_restore():
    assert propose("d1", "QUARANTINED", "HIGH_RISK").action == "isolate"
    assert propose("d1", "RESTORED", "QUARANTINED").action == "restore"
    assert propose("d1", "NORMAL", "NORMAL").action == "none"


def test_observe_only_never_calls_adapter():
    dry = DryRunSwitchAdapter()
    ex = Executor(RuntimeMode.OBSERVE_ONLY, adapter=dry, dry_run_adapter=dry)
    rec = ex.execute(propose("d1", "QUARANTINED", "HIGH_RISK"))
    assert rec.stage == EnforcementStage.EXECUTED and dry.action_log() == []


def test_dry_run_logs_via_dry_run_adapter_only():
    dry = DryRunSwitchAdapter()
    ex = Executor(RuntimeMode.DRY_RUN, adapter=dry, dry_run_adapter=dry)
    rec = ex.execute(propose("d1", "QUARANTINED", "HIGH_RISK"))
    assert rec.stage == EnforcementStage.EXECUTED and len(dry.action_log()) == 1


class _FakeSwitch(SwitchAdapter):
    def __init__(self, verify_ok=True):
        self.verify_ok = verify_ok
        self.isolated = []
    def status(self): return OpStatus.LIVE
    def get_devices(self): return []
    def get_port_status(self, port): return {}
    def get_capabilities(self): return {}
    def isolate_device(self, m):
        self.isolated.append(m)
        return ActionResult(OpStatus.LIVE, "isolated", previous_state={"vlan": 10})
    def restore_device(self, m, prev):
        return ActionResult(OpStatus.LIVE, "restored")
    def verify_isolation(self, m):
        return ActionResult(OpStatus.VERIFIED if self.verify_ok else OpStatus.FAILED, "checked")


def test_enforce_requires_explicit_confirmation():
    sw = _FakeSwitch()
    ex = Executor(RuntimeMode.ENFORCE, adapter=sw, dry_run_adapter=DryRunSwitchAdapter())
    rec = ex.execute(propose("d1", "QUARANTINED", "HIGH_RISK"), confirmed=False)
    assert rec.stage == EnforcementStage.FAILED and sw.isolated == []


def test_enforce_confirmed_reaches_verified():
    sw = _FakeSwitch(verify_ok=True)
    ex = Executor(RuntimeMode.ENFORCE, adapter=sw, dry_run_adapter=DryRunSwitchAdapter())
    rec = ex.execute(propose("d1", "QUARANTINED", "HIGH_RISK"), confirmed=True)
    assert rec.stage == EnforcementStage.VERIFIED and sw.isolated == ["d1"]


def test_enforce_failed_verification_triggers_rollback():
    sw = _FakeSwitch(verify_ok=False)
    ex = Executor(RuntimeMode.ENFORCE, adapter=sw, dry_run_adapter=DryRunSwitchAdapter())
    rec = ex.execute(propose("d1", "QUARANTINED", "HIGH_RISK"), confirmed=True)
    assert rec.stage in (EnforcementStage.ROLLED_BACK, EnforcementStage.FAILED)


def test_verification_never_upgrades_unexpected_status():
    class _Weird(_FakeSwitch):
        def verify_isolation(self, m): return ActionResult(OpStatus.LIVE, "ambiguous")
    r = verify(_Weird(), "d1")
    assert r.status == OpStatus.FAILED
