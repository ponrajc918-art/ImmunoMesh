"""Real packet capture via a Linux AF_PACKET raw socket (Section 5). No scapy dependency.

Requires root or CAP_NET_RAW (checked honestly via security.permissions, not assumed). Falls
back to OpStatus.UNSUPPORTED — never silently pretends to capture — if the socket cannot be
opened or bound.
"""
from __future__ import annotations
import logging
import socket
import time
from collections.abc import Iterator
from immunomesh.integration.capture.base import CaptureAdapter
from immunomesh.integration.capture.pcap import ParsedPacket, parse_ethernet_ipv4
from immunomesh.integration.security.credentials import install_redaction
from immunomesh.integration.security.permissions import check_raw_socket
from immunomesh.integration.status import OpStatus

log = logging.getLogger("immunomesh.integration.capture")
install_redaction(log)
ETH_P_ALL = 0x0003


class RawSocketCaptureAdapter(CaptureAdapter):
    def __init__(self, interface: str, timeout_s: float = 1.0) -> None:
        self.interface, self.timeout_s = interface, timeout_s
        self._sock: socket.socket | None = None
        self._stop = False
        self._status = OpStatus.LIVE
        check = check_raw_socket()
        if not check.ok:
            self._status = OpStatus.UNSUPPORTED
            self._error = check.detail
            return
        try:
            s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
            s.bind((interface, 0))
            s.settimeout(timeout_s)
            self._sock = s
            self._error = None
        except OSError as e:
            self._status, self._error = OpStatus.UNSUPPORTED, str(e)

    def status(self) -> OpStatus:
        return self._status

    def error(self) -> str | None:
        return self._error

    def recv_one(self) -> ParsedPacket | None:
        """Bounded: returns within ~self.timeout_s even if nothing arrives. Safe to call in a
        poll loop (see runtime/live.py) — unlike packets(), it cannot block indefinitely."""
        if self._sock is None:
            return None
        try:
            raw, _addr = self._sock.recvfrom(65535)
        except socket.timeout:
            return None
        except OSError as e:
            if self._stop:
                return None
            log.error("capture error on %s: %s", self.interface, e)
            self._status = OpStatus.FAILED
            return None
        return parse_ethernet_ipv4(raw, time.time())

    def packets(self) -> Iterator[ParsedPacket]:
        if self._sock is None:
            log.warning("capture unsupported on interface %s: %s", self.interface, self._error)
            return
        while not self._stop:
            try:
                raw, _addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError as e:
                if self._stop:
                    return  # closed by stop() from another thread — a clean shutdown, not a failure
                log.error("capture error on %s: %s", self.interface, e)
                self._status = OpStatus.FAILED
                return
            pkt = parse_ethernet_ipv4(raw, time.time())
            if pkt is not None:
                yield pkt

    def stop(self) -> None:
        self._stop = True
        if self._sock is not None:
            self._sock.close()
