"""RTSP presence check (Section 9): a read-only TCP connect + RTSP OPTIONS banner check on
port 554. Never opens a video stream, never sends credentials."""
from __future__ import annotations
import socket
from immunomesh.integration.camera.base import CameraAdapter, CameraObservation

RTSP_PORT = 554


class RTSPObservationAdapter(CameraAdapter):
    def __init__(self, timeout_s: float = 1.5) -> None:
        self.timeout_s = timeout_s

    def observe(self, ip: str) -> CameraObservation:
        try:
            with socket.create_connection((ip, RTSP_PORT), timeout=self.timeout_s) as s:
                s.sendall(f"OPTIONS rtsp://{ip}:{RTSP_PORT}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode())
                s.settimeout(self.timeout_s)
                resp = s.recv(512)
            detected = resp.startswith(b"RTSP/1.0")
            return CameraObservation(ip, detected, False, "RTSP OPTIONS banner received" if detected
                                     else f"port {RTSP_PORT} open but no RTSP banner")
        except (OSError, socket.timeout) as e:
            return CameraObservation(ip, False, False, f"no RTSP service detected on {RTSP_PORT}: {e}")
