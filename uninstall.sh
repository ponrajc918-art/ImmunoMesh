#!/usr/bin/env bash
# Stops and removes the systemd service if installed; does NOT remove the repository or
# results/ data (left for the user to decide what to keep).
set -euo pipefail
if systemctl list-unit-files 2>/dev/null | grep -q immunomesh.service; then
    sudo systemctl stop immunomesh.service || true
    sudo systemctl disable immunomesh.service || true
    sudo rm -f /etc/systemd/system/immunomesh.service
    sudo systemctl daemon-reload
    echo "Removed the immunomesh systemd service."
else
    echo "No immunomesh systemd service found; nothing to do."
fi
echo "Python packages and the repository itself were left in place."
