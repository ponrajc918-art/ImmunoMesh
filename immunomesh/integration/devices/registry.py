"""In-memory device registry (Section 4), optionally persisted to SQLite via storage.audit-style
access. Not a scanner: only records what discovery adapters or observed flows report."""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from immunomesh.integration.devices.classification import classify
from immunomesh.integration.devices.identity import Device
from immunomesh.integration.discovery.base import DiscoveredDevice


class DeviceRegistry:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.devices: dict[str, Device] = {}
        self.con = None
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.con = sqlite3.connect(str(db_path))
            self.con.execute("""CREATE TABLE IF NOT EXISTS devices(ip TEXT PRIMARY KEY, mac TEXT, hostname TEXT,
                vendor TEXT, interface TEXT, first_seen REAL, last_seen REAL, device_type TEXT,
                confidence REAL, sources TEXT, observed_ports TEXT)""")
            self.con.commit()

    def observe_discovery(self, d: DiscoveredDevice, interface: str | None = None) -> Device:
        now = time.time()
        dev = self.devices.get(d.ip)
        if dev is None:
            dev = Device(ip=d.ip, mac=d.mac, hostname=d.hostname, vendor=d.vendor, interface=interface,
                        first_seen=now, last_seen=now)
            self.devices[d.ip] = dev
        dev.last_seen = now
        dev.mac = dev.mac or d.mac
        dev.hostname = dev.hostname or d.hostname
        dev.sources.add(d.source)
        return dev

    def observe_flow(self, src_ip: str, port: int | None, interface: str | None = None) -> Device:
        now = time.time()
        dev = self.devices.get(src_ip)
        if dev is None:
            dev = Device(ip=src_ip, interface=interface, first_seen=now, last_seen=now)
            self.devices[src_ip] = dev
        dev.last_seen = now
        dev.sources.add("flow_observation")
        if port is not None:
            dev.observed_ports.add(port)
        c = classify(dev.observed_ports)
        dev.device_type, dev.confidence = c.device_type, c.confidence
        return dev

    def persist(self) -> None:
        if self.con is None:
            return
        rows = [tuple(d.as_row().values()) for d in self.devices.values()]
        self.con.executemany("INSERT OR REPLACE INTO devices VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        self.con.commit()

    def as_dataframe(self):
        import pandas as pd
        return pd.DataFrame([d.as_row() for d in self.devices.values()])
