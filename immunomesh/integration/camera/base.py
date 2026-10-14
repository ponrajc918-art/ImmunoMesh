"""Camera adapter interface (Section 9). Explicitly does NOT access video content — the
cybersecurity objective is the camera's network behaviour, not its stream."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from immunomesh.integration.status import OpStatus


@dataclass
class CameraObservation:
    ip: str
    rtsp_detected: bool
    onvif_detected: bool
    detail: str


class CameraAdapter(ABC):
    @abstractmethod
    def observe(self, ip: str) -> CameraObservation: ...
