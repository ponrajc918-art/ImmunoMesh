"""Heuristic device-type classification from observed ports/protocols (Section 8/9).

Maps onto the existing simulator's device_type vocabulary (camera/sensor/plc, schema.DEVICE_TYPES)
where the evidence is reasonably clear, so the existing per-type baseline/imputation/evidence code
(fit fresh on live baseline data, never on simulator data) has a meaningful grouping. Anything not
confidently matched stays "unknown" — an honest out-of-vocabulary label — rather than being forced
into one of the three categories. See docs/hardware/packet_capture.md for what "unknown" costs.
"""
from __future__ import annotations
from dataclasses import dataclass

RTSP_PORT, ONVIF_PORT, HTTPS_PORT, SSH_PORT, MODBUS_PORT, HTTP_PORT = 554, 80, 443, 22, 502, 8080


@dataclass
class Classification:
    device_type: str
    confidence: float
    reason: str


def classify(observed_ports: set[int]) -> Classification:
    if RTSP_PORT in observed_ports or ONVIF_PORT in observed_ports and 3702 in observed_ports:
        return Classification("camera", 0.85, "RTSP/ONVIF port observed")
    if MODBUS_PORT in observed_ports:
        return Classification("plc", 0.85, "Modbus (502/TCP) observed")
    if SSH_PORT in observed_ports and len(observed_ports) <= 3:
        return Classification("sensor", 0.4, "SSH-only low-port-diversity host (weak signal, treated as generic IoT/sensor)")
    if observed_ports:
        return Classification("unknown", 0.2, f"no confident signature in observed ports {sorted(observed_ports)}")
    return Classification("unknown", 0.0, "no ports observed yet")
