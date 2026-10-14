"""System health checks (Section 23/28) — every check performs the real probe, never assumes."""
from __future__ import annotations
import importlib
import importlib.util
from dataclasses import dataclass
from immunomesh.integration.capture.interface import list_interfaces, default_interface
from immunomesh.integration.discovery.arp import ARPDiscovery
from immunomesh.integration.security.permissions import check_raw_socket, check_root
from immunomesh.integration.status import HealthState, OpStatus


@dataclass
class CheckResult:
    name: str
    state: HealthState
    detail: str


def check_python() -> CheckResult:
    import sys
    ok = sys.version_info >= (3, 10)
    return CheckResult("python", HealthState.HEALTHY if ok else HealthState.DEGRADED, sys.version.split()[0])


def check_dependencies() -> CheckResult:
    missing = [m for m in ("numpy", "pandas", "sklearn", "yaml", "joblib") if importlib.util.find_spec(m) is None]
    return CheckResult("dependencies", HealthState.HEALTHY if not missing else HealthState.FAILED,
                       "all present" if not missing else f"missing: {missing}")


def check_interface() -> CheckResult:
    ifaces = list_interfaces()
    if not ifaces:
        return CheckResult("interface", HealthState.FAILED, "no interfaces found (/sys/class/net unavailable)")
    d = default_interface()
    return CheckResult("interface", HealthState.HEALTHY, f"{len(ifaces)} interface(s), default={d}")


def check_capture_permission() -> CheckResult:
    c = check_raw_socket()
    return CheckResult("capture_permission", HealthState.HEALTHY if c.ok else HealthState.DEGRADED, c.detail)


def check_root_priv() -> CheckResult:
    c = check_root()
    return CheckResult("root_privilege", HealthState.HEALTHY if c.ok else HealthState.DEGRADED, c.detail)


def check_discovery() -> CheckResult:
    a = ARPDiscovery()
    ok = a.status() == OpStatus.LIVE
    return CheckResult("discovery", HealthState.HEALTHY if ok else HealthState.DEGRADED,
                       "ARP table readable" if ok else "ARP table unavailable")


def check_detector() -> CheckResult:
    try:
        from immunomesh.config import load_config
        from immunomesh.pipeline import fit_baseline
        load_config()
        return CheckResult("detector", HealthState.HEALTHY, "config + pipeline import OK")
    except Exception as e:
        return CheckResult("detector", HealthState.FAILED, str(e))


def check_dashboard() -> CheckResult:
    ok = importlib.util.find_spec("streamlit") is not None
    return CheckResult("dashboard", HealthState.HEALTHY if ok else HealthState.DEGRADED,
                       "streamlit importable" if ok else "streamlit not installed")


def run_all() -> list[CheckResult]:
    return [check_python(), check_dependencies(), check_interface(), check_capture_permission(),
            check_root_priv(), check_discovery(), check_detector(), check_dashboard()]
