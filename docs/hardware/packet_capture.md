# Packet capture

`capture/raw_socket.py` uses a Linux `AF_PACKET`/`SOCK_RAW` socket (stdlib `socket` only — no
scapy dependency) bound to one interface. `capture/pcap.py` parses Ethernet + IPv4 + TCP/UDP/ICMP
headers by hand; anything else (IPv6, VLAN-tagged frames, other IP protocols) is out of scope and
simply not parsed — not guessed at.

**Permissions**: needs root or `CAP_NET_RAW`. `security/permissions.check_raw_socket()` actually
attempts to open the socket rather than assuming; `doctor` reports the real result.

**Flow-to-schema mapping** (also documented as the authoritative version in `capture/flow.py`'s
module docstring — keep both in sync if either changes):

| Real flow field | ImmunoMesh schema field |
|---|---|
| flow start time | `timestamp` |
| LAN-side endpoint | `src_id` (IP string) |
| far-side endpoint | `dst_id` (IP string) |
| classifier output (devices/classification.py) | `device_type` ("unknown" if unclassified) |
| TCP/UDP/ICMP | `protocol` |
| LAN-side port | `src_port` |
| far-side port | `dst_port` |
| packets both directions | `packet_count` |
| bytes both directions | `byte_count` |
| flow duration | `duration_s` |
| SYN seen, no matching ACK from far side | `failed_conn` |
| private/public heuristic | `direction` |
| (no ground truth for live traffic) | `label=-1`, `attack_type="unknown"` |

**Known limitation**: a device the classifier cannot confidently place in camera/plc/sensor gets
`device_type="unknown"` — an out-of-vocabulary value for the existing one-hot encoder. This
degrades gracefully (zero one-hot columns), not a crash, but the per-device-type median
imputation and evidence baseline lose some resolution for that device. The per-*device* (by
`src_id`) baseline used by the detector itself is unaffected.
