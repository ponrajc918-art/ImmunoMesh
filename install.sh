#!/usr/bin/env bash
# ImmunoMesh edge install (Section 29). Run as root (needed for raw-socket packet capture).
set -euo pipefail
cd "$(dirname "$0")"
RUNTIME_ONLY="${1:-}"

python3 -m pip install --break-system-packages -r requirements-runtime.txt
if [ "$RUNTIME_ONLY" != "--runtime-only" ]; then
    python3 -m pip install --break-system-packages -r requirements-dev.txt
fi

echo
echo "Install complete. Next steps:"
echo "  sudo python3 -m immunomesh.cli setup     # detect interfaces, write immunomesh.yaml"
echo "  sudo python3 -m immunomesh.cli doctor    # confirm readiness"
echo "  sudo python3 -m immunomesh.cli edge      # start the headless edge runtime (OBSERVE_ONLY)"
echo
echo "To install as a systemd service, see systemd/immunomesh.service and docs/hardware/deployment.md."
