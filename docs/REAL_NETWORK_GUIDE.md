# Real-network guide

ImmunoMesh can now observe real network traffic through a Raspberry Pi/Linux edge node, in
addition to its original software simulation (Phases 1-10, unchanged and frozen). Honest framing
(the only one this project claims): *"a modular cybersecurity monitoring and response platform
that operates in simulation and can be deployed as a Raspberry Pi-based edge sensor for
authorized real-network environments, with pluggable device and network-control adapters."* Not
universal plug-and-play — not every switch/camera/AP vendor has a working adapter.

## What hardware is required
- A Linux host with a network interface that can see the traffic you want to monitor (a port
  mirror/SPAN port on a managed switch, or the host's own traffic). Raspberry Pi is the intended
  edge target but any Linux box works — this project was built and tested on neither (see
  `docs/hardware/raspberry_pi.md` for the honest scope).
- Root or `CAP_NET_RAW` for packet capture.

## What hardware is optional
- A managed switch with SNMP or SSH access, if you want real enforcement (isolation). Without
  one, the system still fully observes and generates evidence/trust/response state — it just
  can't act on `QUARANTINED` beyond logging it.
- An IP camera — only needed if you want to see camera-specific classification exercised; the
  system monitors any device's traffic regardless.

## How to connect it
See `docs/hardware/deployment.md` for the exact command sequence; `docs/hardware/troubleshooting.md`
for when something doesn't work.

## How to discover it
`python -m immunomesh.cli discover` — passive only (reads the ARP table, listens for mDNS if
`zeroconf` is installed). Never sends active scans. Devices also accumulate automatically from
observed traffic once `capture`/`monitor`/`edge` is running.

## How to start observation
`python -m immunomesh.cli edge --headless` (or `monitor` in the foreground for a bounded test
run). Starts in `BASELINE_COLLECTION`; once enough baseline flows are seen it switches to
`MONITORING` and starts scoring flows with the Isolation Forest and updating per-device trust,
reusing the existing, unmodified feature pipeline, detector, evidence and trust code
(`docs/hardware/architecture.md`). Evidence is computed but not persisted. Peer consensus, the
response state machine and the enforcement executor are **not** wired into this runtime: they exist
(and are unit-tested against fakes) but `monitor`/`edge` never call them.

## How to enable dry-run
Set `runtime.mode: dry_run` in `config/live.yaml`. Enforcement decisions are computed and logged
exactly as they would be for real, but only ever reach `switch/dry_run.py`.

## How enforcement works / how rollback works
See `docs/hardware/enforcement.md` — the full `REQUESTED -> ... -> VERIFIED/FAILED/ROLLED_BACK`
contract, and why `ENFORCE` mode refuses without explicit confirmation.

## How to troubleshoot
`docs/hardware/troubleshooting.md`.

## What was actually validated in this project
A full HIL *self-test* — real packet capture, on this build environment's own loopback
interface, with real (locally generated) TCP traffic, run through the complete unmodified
pipeline end to end. See `results/hil/RESULTS.md` for the measured numbers and
`results/hil/run_manifest.json` for exactly what was and wasn't involved. **No physical
Raspberry Pi, managed switch, or IP camera was available or used** — this guide documents how to
run the same thing against real hardware; it does not claim that was already done.
