"""Common data model: column names shared by every module."""
RAW_COLUMNS = [
    "timestamp", "src_id", "dst_id", "device_type", "protocol", "src_port", "dst_port",
    "packet_count", "byte_count", "duration_s", "failed_conn", "direction",
    "label", "attack_type",
]
NUMERIC_RAW = ["src_port", "dst_port", "packet_count", "byte_count", "duration_s", "failed_conn"]
CATEGORICAL = ["protocol", "direction", "device_type"]
PROTOCOLS = ["TCP", "UDP", "ICMP"]
DIRECTIONS = ["outbound", "inbound"]
DEVICE_TYPES = ["camera", "sensor", "plc"]

# Engineered features (Phase 4) fed to the detector
ENGINEERED = [
    "packet_rate", "byte_rate", "log_packets", "log_bytes", "duration_s",
    "conn_freq", "failed_ratio", "dest_diversity", "dport_diversity",
    "src_dst_freq", "protocol_share", "new_destination",
    "pkt_rate_dev", "byte_rate_dev", "burst_indicator",
]

# Simulation clock origin used by the traffic generator (generate_traffic default t_start).
T_START = 1_700_000_000.0
