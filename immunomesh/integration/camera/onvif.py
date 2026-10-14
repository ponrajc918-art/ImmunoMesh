"""ONVIF WS-Discovery probe (Section 9), stdlib multicast only — no onvif/zeep dependency needed
for discovery (only full device-management calls would need those). Sends one standard WS-Discovery
Probe to 239.255.255.250:3702 and listens briefly; reports exactly what came back, or nothing."""
from __future__ import annotations
import socket
import time
import uuid
from immunomesh.integration.camera.base import CameraObservation

WSD_ADDR, WSD_PORT = "239.255.255.250", 3702
_PROBE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">
  <e:Header>
    <w:MessageID>uuid:{msgid}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe>
  </e:Body>
</e:Envelope>"""


def probe(timeout_s: float = 2.0) -> list[CameraObservation]:
    """One real multicast probe on the network this container/host is attached to. Returns []
    (never fabricated entries) if nothing answers within timeout_s."""
    msg = _PROBE.format(msgid=uuid.uuid4()).encode()
    found: list[CameraObservation] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        s.settimeout(timeout_s)
        s.sendto(msg, (WSD_ADDR, WSD_PORT))
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                data, addr = s.recvfrom(8192)
            except socket.timeout:
                break
            found.append(CameraObservation(addr[0], rtsp_detected=False, onvif_detected=True,
                                           detail=f"WS-Discovery ProbeMatch received ({len(data)} bytes)"))
        s.close()
    except OSError as e:
        return [CameraObservation("", False, False, f"WS-Discovery probe could not be sent: {e}")]
    return found
