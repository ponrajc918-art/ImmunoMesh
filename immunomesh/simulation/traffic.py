"""Synthetic network-flow simulator (no real traffic is generated or sent).

Every record is a flow-like row. Normal behaviour follows simple per-device-type
profiles (periodic camera stream, MQTT sensor, Modbus-like PLC polling, DNS/NTP).
Anomalies are injected in labelled windows on selected devices; during a window the
device's normal flows are replaced by attack-pattern flows (label=1).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from immunomesh.config import SimulationConfig
from immunomesh.schema import RAW_COLUMNS

SERVERS = ["nvr", "broker", "scada", "dns", "ntp"]
EXTERNAL = ["ext_198.51.100.7", "ext_203.0.113.9", "ext_192.0.2.44"]  # documentation ranges

# type -> (period_s, dst, proto, dport, pkts(mu,sd), bytes(mu,sd), dur(mu,sd))
PROFILES = {
    "camera": (1.0, "nvr", "UDP", 5004, (60, 6), (70000, 8000), (1.0, 0.05)),
    "sensor": (5.0, "broker", "TCP", 1883, (8, 1), (900, 120), (0.3, 0.05)),
    "plc": (2.0, "scada", "TCP", 502, (12, 2), (1400, 200), (0.2, 0.04)),
}


def build_devices(cfg: SimulationConfig) -> list[tuple[str, str]]:
    devs = [(f"cam_{i:02d}", "camera") for i in range(1, cfg.n_cameras + 1)]
    devs += [(f"sensor_{i:02d}", "sensor") for i in range(1, cfg.n_sensors + 1)]
    devs += [(f"plc_{i:02d}", "plc") for i in range(1, cfg.n_plcs + 1)]
    return devs


def _rows(ts, src, dst, dtype, proto, sport, dport, pk, by, du, failed, label, attack):
    n = len(ts)
    return pd.DataFrame({
        "timestamp": ts, "src_id": src, "dst_id": dst, "device_type": dtype,
        "protocol": proto, "src_port": sport, "dst_port": dport,
        "packet_count": np.maximum(np.round(pk), 1), "byte_count": np.maximum(np.round(by), 40),
        "duration_s": np.maximum(du, 0.001), "failed_conn": failed,
        "direction": "outbound", "label": label, "attack_type": attack,
    }) if n else pd.DataFrame(columns=RAW_COLUMNS)


def _normal_flows(rng, dev, dtype, duration):
    period, dst, proto, dport, pk, by, du = PROFILES[dtype]
    ts = np.arange(rng.uniform(0, period), duration, period)
    ts = ts + rng.normal(0, 0.05 * period, len(ts))
    n = len(ts)
    parts = [_rows(ts, dev, dst, dtype, proto, rng.integers(32768, 61000, n), dport,
                   rng.normal(*pk, n), rng.normal(*by, n), rng.normal(*du, n),
                   (rng.random(n) < 0.005).astype(int), 0, "none")]
    # auxiliary DNS (all) and NTP (plc) traffic
    for aux_dst, aport, every in [("dns", 53, 30.0)] + ([("ntp", 123, 64.0)] if dtype == "plc" else []):
        t = np.arange(rng.uniform(0, every), duration, every)
        m = len(t)
        parts.append(_rows(t, dev, aux_dst, dtype, "UDP", rng.integers(32768, 61000, m), aport,
                           np.full(m, 2.0), rng.normal(120, 10, m), rng.normal(0.05, 0.01, m),
                           np.zeros(m, dtype=int), 0, "none"))
    return pd.concat(parts, ignore_index=True)


def _attack_flows(rng, dev, dtype, kind, t0, t1, m):
    """Attack-pattern flows for window [t0, t1). m = intensity multiplier (low=3, high=10)."""
    L = t1 - t0
    period, dst, proto, dport, pk, by, du = PROFILES[dtype]
    lab = 1
    if kind == "traffic_spike":
        n = int(L * m / period)
        ts = rng.uniform(t0, t1, n)
        f = m / 2
        return _rows(ts, dev, dst, dtype, proto, rng.integers(32768, 61000, n), dport,
                     rng.normal(pk[0] * f, pk[1], n), rng.normal(by[0] * f, by[1], n),
                     rng.normal(du[0], du[1], n), (rng.random(n) < 0.01).astype(int), lab, kind)
    if kind == "port_scan":
        n = int(L * m)
        ts = rng.uniform(t0, t1, n)
        return _rows(ts, dev, rng.choice(SERVERS, n), dtype, "TCP", rng.integers(32768, 61000, n),
                     rng.integers(1, 1025, n), rng.integers(1, 3, n), rng.uniform(40, 100, n),
                     rng.uniform(0.005, 0.05, n), (rng.random(n) < 0.85).astype(int), lab, kind)
    if kind == "brute_force":
        n = int(L * m / 2)
        ts = rng.uniform(t0, t1, n)
        return _rows(ts, dev, np.full(n, "scada"), dtype, "TCP", rng.integers(32768, 61000, n), 22,
                     rng.integers(6, 11, n), rng.uniform(500, 900, n), rng.uniform(0.2, 0.5, n),
                     (rng.random(n) < 0.9).astype(int), lab, kind)
    if kind == "exfiltration":
        n = max(int(L * m / 5), 1)
        ts = rng.uniform(t0, t1, n)
        b = rng.normal(30000 * m, 3000 * m, n)
        return _rows(ts, dev, rng.choice(EXTERNAL, n), dtype, "TCP", rng.integers(32768, 61000, n),
                     443, b / 1200, b, rng.uniform(3, 8, n), np.zeros(n, dtype=int), lab, kind)
    if kind == "protocol_irregularity":
        n = int(L * m / 2)
        ts = rng.uniform(t0, t1, n)
        icmp = rng.random(n) < 0.5
        proto_arr = np.where(icmp, "ICMP", "UDP")
        dport_arr = np.where(icmp, 0, rng.integers(1024, 65536, n))
        return _rows(ts, dev, rng.choice(SERVERS + EXTERNAL, n), dtype, proto_arr,
                     rng.integers(32768, 61000, n), dport_arr, rng.integers(3, 11, n),
                     rng.uniform(300, 1000, n), rng.uniform(0.01, 0.3, n),
                     (rng.random(n) < 0.1).astype(int), lab, kind)
    raise ValueError(kind)


def _corrupt(df: pd.DataFrame, cfg: SimulationConfig, rng) -> pd.DataFrame:
    """Inject missing values, duplicates and invalid records so the cleaner has work to do."""
    df = df.copy()
    n = len(df)
    for col in ("packet_count", "byte_count", "duration_s"):
        df.loc[rng.random(n) < cfg.missing_rate, col] = np.nan
    bad = rng.random(n) < cfg.invalid_rate
    df.loc[bad, "byte_count"] = -1.0
    dups = df[rng.random(n) < cfg.duplicate_rate]
    return pd.concat([df, dups], ignore_index=True)


def generate_traffic(cfg: SimulationConfig, seed: int, with_anomalies: bool,
                     duration_s: float | None = None, corrupt: bool = True,
                     t_start: float = 1_700_000_000.0) -> pd.DataFrame:
    """Generate one labelled flow table. Deterministic for a given (cfg, seed)."""
    rng = np.random.default_rng(seed)
    duration = duration_s or (cfg.eval_duration_s if with_anomalies else cfg.train_duration_s)
    devices = build_devices(cfg)
    m = 10.0 if cfg.intensity == "high" else 3.0

    windows: dict[str, list[tuple[str, float, float]]] = {}
    if with_anomalies:
        idx = rng.choice(len(devices), cfg.anomalous_device_count, replace=False)
        slot = duration / cfg.windows_per_device
        for i in idx:
            dev = devices[i][0]
            windows[dev] = []
            for k in range(cfg.windows_per_device):
                lo = k * slot
                start = rng.uniform(lo, lo + slot - cfg.window_length_s)
                windows[dev].append((str(rng.choice(cfg.attack_types)), start, start + cfg.window_length_s))

    parts = []
    for dev, dtype in devices:
        normal = _normal_flows(rng, dev, dtype, duration)
        for kind, t0, t1 in windows.get(dev, []):
            normal = normal[~((normal.timestamp >= t0) & (normal.timestamp < t1))]
            parts.append(_attack_flows(rng, dev, dtype, kind, t0, t1, m))
        parts.append(normal)
    df = pd.concat(parts, ignore_index=True)
    df = df[(df.timestamp >= 0) & (df.timestamp < duration)]
    df["timestamp"] = t_start + df["timestamp"]
    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    df = df[RAW_COLUMNS]
    if corrupt:
        df = _corrupt(df, cfg, rng).sort_values("timestamp", kind="stable").reset_index(drop=True)
    df.attrs["attack_windows"] = windows
    return df
