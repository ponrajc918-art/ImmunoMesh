# Deployment

```
./install.sh                                    # pip installs (add --runtime-only to skip dev extras)
sudo python3 -m immunomesh.cli setup             # writes immunomesh.yaml from detected interfaces
sudo python3 -m immunomesh.cli doctor            # confirms readiness — read every line
sudo python3 -m immunomesh.cli discover          # passive ARP/mDNS snapshot
sudo python3 -m immunomesh.cli capture --duration 10   # sanity-check real traffic is seen
sudo python3 -m immunomesh.cli monitor --cycles 20     # foreground OBSERVE_ONLY loop
sudo python3 -m immunomesh.cli edge --headless         # production loop (systemd/immunomesh.service)
```

Copy `systemd/immunomesh.service` to `/etc/systemd/system/`, edit `WorkingDirectory`, then
`sudo systemctl daemon-reload && sudo systemctl enable --now immunomesh`.

`config/live.yaml` always starts `runtime.mode: observe_only`, `enforcement.enabled: false`.
Escalate deliberately: `observe_only` -> `dry_run` (exercises `switch/dry_run.py`, no real
actions) -> `enforce` (requires `enforcement.enabled: true` too — `LiveConfig.validate()` refuses
any other combination, by design: ENFORCE is never entered silently). Credentials for a real switch adapter go in environment
variables (`IMMUNOMESH_SWITCH_USERNAME`/`_PASSWORD`), never in `config/live.yaml`.
