"""Capture adapter interface (Section 4). Concrete adapters must report OpStatus honestly."""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Iterator
from immunomesh.integration.capture.pcap import ParsedPacket
from immunomesh.integration.status import OpStatus


class CaptureAdapter(ABC):
    @abstractmethod
    def status(self) -> OpStatus: ...

    @abstractmethod
    def packets(self) -> Iterator[ParsedPacket]:
        """Stream indefinitely (for a dedicated background thread). Blocks between packets."""

    def recv_one(self) -> ParsedPacket | None:
        """One bounded receive attempt: returns a packet, or None if none arrived within the
        adapter's own internal timeout. Never blocks longer than that timeout. Poll-based
        callers (LiveRuntime) MUST use this rather than `packets()`, which can legitimately
        block forever on a quiet link and is only safe to drain from its own dedicated thread."""
        raise NotImplementedError(f"{type(self).__name__} does not support bounded polling")

    @abstractmethod
    def stop(self) -> None: ...
