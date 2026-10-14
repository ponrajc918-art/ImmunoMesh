"""mDNS discovery (Section 4). Best-effort: uses the `zeroconf` package if installed, else
reports UNSUPPORTED honestly rather than faking a listener."""
from __future__ import annotations
from immunomesh.integration.discovery.base import DiscoveryAdapter, DiscoveredDevice
from immunomesh.integration.status import OpStatus

try:
    import zeroconf as _zeroconf_mod  # noqa: F401
    _HAVE_ZEROCONF = True
except ImportError:
    _HAVE_ZEROCONF = False


class MDNSDiscovery(DiscoveryAdapter):
    def __init__(self, timeout_s: float = 2.0) -> None:
        self.timeout_s = timeout_s
        self._status = OpStatus.UNSUPPORTED if not _HAVE_ZEROCONF else OpStatus.LIVE

    def status(self) -> OpStatus:
        return self._status

    def discover(self) -> list[DiscoveredDevice]:
        if not _HAVE_ZEROCONF:
            return []
        # Real mDNS browsing requires the zeroconf package (not installed in this environment by
        # default — see requirements-runtime.txt). Left as a documented extension point rather
        # than a fabricated listener: no result is returned unless zeroconf is actually present
        # AND actual responses are observed.
        from zeroconf import Zeroconf, ServiceBrowser  # local import, only reached if installed
        found: list[DiscoveredDevice] = []

        class _Listener:
            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info and info.parsed_addresses():
                    found.append(DiscoveredDevice(ip=info.parsed_addresses()[0], mac=None,
                                                  source="mdns", hostname=name, confidence=0.6))
            def remove_service(self, *a, **k): pass
            def update_service(self, *a, **k): pass

        zc = Zeroconf()
        try:
            for svc in ("_services._dns-sd._udp.local.",):
                ServiceBrowser(zc, svc, _Listener())
            import time; time.sleep(self.timeout_s)
        finally:
            zc.close()
        return found
