# Raspberry Pi deployment

`python -m immunomesh.cli edge --headless` is the target entry point. It was
**built and tested in this environment on generic Linux, not on physical Raspberry Pi hardware**
— `hardware_detect.detect_raspberry_pi()` checks `/proc/cpuinfo` for a Raspberry Pi/BCM SoC
string and honestly reports "not detected" here (see `results/hil/run_manifest.json`).

What should port unchanged to a real Pi: everything in `capture/`, `devices/`, `discovery/arp.py`,
`runtime/`, `enforcement/`, `storage.audit` — all stdlib + the packages in
`requirements-runtime.txt`, no architecture-specific code.

What to verify on real hardware before trusting results: raw-socket throughput at real network
speeds (this was only tested against a handful of local connections, not sustained traffic);
`list_interfaces()`/`default_interface()` against a real Pi's `eth0`/`wlan0` naming; running as a
non-root user with `CAP_NET_RAW` via `setcap` instead of full root (the systemd unit here still
uses root for simplicity — tightening this is listed in Limitations).
