"""Credential loading (Section 18). Credentials are NEVER hardcoded, logged, or persisted to
results/config files — only read from environment variables at call time."""
from __future__ import annotations
import logging
import os
import re
from dataclasses import dataclass

_SECRET_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"(password|passwd|pwd|secret|token|api[_-]?key)\s*[=:]\s*\S+",
]]


class RedactingFilter(logging.Filter):
    """Attached to every logger the integration layer uses; scrubs anything secret-shaped."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in _SECRET_PATTERNS:
            msg = pat.sub(lambda m: m.group(0).split("=")[0].split(":")[0] + "=<redacted>", msg)
        record.msg, record.args = msg, ()
        return True


def install_redaction(logger: logging.Logger) -> None:
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())


@dataclass(frozen=True)
class Credential:
    username: str | None
    password: str | None
    source: str  # which env vars were used, for audit — never the values themselves

    def redacted(self) -> dict:
        return {"username": self.username, "password": "<redacted>" if self.password else None, "source": self.source}


def load_credential(prefix: str) -> Credential | None:
    """Load IMMUNOMESH_{PREFIX}_USERNAME / _PASSWORD from the environment. Returns None if unset.
    e.g. load_credential("SWITCH") reads IMMUNOMESH_SWITCH_USERNAME / IMMUNOMESH_SWITCH_PASSWORD.
    """
    u = os.environ.get(f"IMMUNOMESH_{prefix}_USERNAME")
    p = os.environ.get(f"IMMUNOMESH_{prefix}_PASSWORD")
    if not u and not p:
        return None
    return Credential(u, p, source=f"env:IMMUNOMESH_{prefix}_USERNAME/PASSWORD")
