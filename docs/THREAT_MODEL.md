# Threat model

**In scope (simulated):** an attacker on the same network segment as monitored IoT/industrial
devices performing traffic spikes/floods, TCP port scanning, brute-force login attempts against
a service port, data exfiltration to an external host, and protocol irregularities (unexpected
ICMP/ports). The simulator (`immunomesh/simulation/traffic.py`) generates labelled synthetic
flow records for these; **no real packets are sent and no real attack is executed.**

**Explicitly out of scope:** compromise of the ImmunoMesh software itself, compromise or
collusion of the simulated peer monitors, adversarial evasion of the specific feature set,
network-level attacks on the monitoring channel (delay, drop, spoofed peer reports), physical
tampering with edge hardware (none is used), and any attack type not in the simulator's list.

**Trust/consensus assumptions:** peer "sensors" share the same feature pipeline and training
distribution, so their opinions are correlated by construction — this is a simplification, not
a proof of independence. Peer visibility and trust weighting are heuristics, not a validated
distributed protocol.

**Response assumptions:** "quarantine" is a state label only. In a real deployment this would
need to map to an actual control (e.g. switch port disable, firewall rule) which is explicitly
future work and is not implemented or claimed here.
