# Evidence examples (auto-generated from the demo run; synthetic data)

## brute_force

```
Event: Device plc_02
Detection: Anomalous
Evidence:
  - Failed-connection ratio above baseline
  - Burst behaviour above baseline
  - Packet rate below device baseline
  - Byte rate below device baseline
Model: IsolationForest
Score: 0.6921 (threshold 0.6583)
Evidence strength: 0.88 (corroborated)
```

## exfiltration

```
Event: Device cam_03
Detection: Anomalous
Evidence:
  - Burst behaviour above baseline
  - Packet rate below device baseline
  - Flow duration above baseline
  - Destination diversity above baseline
Model: IsolationForest
Score: 0.6593 (threshold 0.6583)
Evidence strength: 0.86 (corroborated)
```

## protocol_irregularity

```
Event: Device plc_02
Detection: Anomalous
Evidence:
  - Failed-connection ratio above baseline
  - Burst behaviour above baseline
  - Destination-port diversity above baseline
  - Protocol mix below baseline (share of flows with this protocol)
  - Bytes per flow below baseline
Model: IsolationForest
Score: 0.6953 (threshold 0.6583)
Evidence strength: 1.00 (corroborated)
```

## false positive (normal flow flagged)

```
Event: Device cam_03
Detection: Anomalous
Evidence:
  - Byte rate below device baseline
  - Burst behaviour above baseline
  - Packet rate below device baseline
  - Bytes per flow below baseline
  - Packets per flow below baseline
Model: IsolationForest
Score: 0.6605 (threshold 0.6583)
Evidence strength: 1.00 (corroborated)
```
