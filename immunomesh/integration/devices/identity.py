"""Device identity record (Section 4)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Device:
    ip: str
    mac: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    interface: str | None = None
    first_seen: float = 0.0
    last_seen: float = 0.0
    device_type: str = "unknown"     # "camera" | "plc" | "sensor" | "unknown" (see classification.py)
    confidence: float = 0.0
    sources: set = field(default_factory=set)   # e.g. {"arp", "flow_observation"}
    observed_ports: set = field(default_factory=set)

    def as_row(self) -> dict:
        return {"ip": self.ip, "mac": self.mac, "hostname": self.hostname, "vendor": self.vendor,
                "interface": self.interface, "first_seen": self.first_seen, "last_seen": self.last_seen,
                "device_type": self.device_type, "confidence": round(self.confidence, 3),
                "sources": ",".join(sorted(self.sources)), "observed_ports": ",".join(map(str, sorted(self.observed_ports)))}
