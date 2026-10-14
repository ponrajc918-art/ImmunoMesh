# ImmunoMesh HIL self-test results

**Scope**: Real packet capture on this container's own loopback interface, with locally generated TCP traffic. NO physical Raspberry Pi, managed switch, or IP camera was used or is claimed. This validates the real-capture code path end-to-end, not a physical deployment.

- Interface: `lo`
- Raspberry Pi detected: False (no Raspberry Pi / BCM SoC signature in /proc/cpuinfo (this is generic Linux hardware/container))
- Real TCP connections generated (loopback): 133
- Real packets captured: 2640
- Flows closed: 264  ·  Dropped packets: 0
- Supervisor cycles run: 40  ·  failures: 0  ·  final health: healthy
- Final runtime state: MONITORING

## Devices observed (1)

| ip        | mac   | hostname   | vendor   | interface   |   first_seen |   last_seen | device_type   |   confidence | sources          | observed_ports                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|:----------|:------|:-----------|:---------|:------------|-------------:|------------:|:--------------|-------------:|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 127.0.0.1 |       |            |          |             |  1.79091e+09 | 1.79091e+09 | unknown       |          0.2 | flow_observation | 32808,33005,33019,33096,33105,33124,33125,33178,33182,33322,33329,33446,33841,33948,34337,34367,34488,34521,34737,34775,34970,35030,35054,35306,35341,35399,35430,35593,35707,35839,35840,35992,36160,36164,36183,36333,36399,36436,36527,36639,37036,37068,37200,37300,37325,37579,37585,37711,37738,37952,38096,38135,38158,38170,38281,38304,38392,38410,38419,38638,38640,38647,38663,38708,38730,38858,38864,39123,39190,39245,39343,39383,39465,39640,39650,39662,40090,40118,40135,40539,40559,40574,40610,40676,40755,40797,40833,40913,41060,41121,41327,41703,42395,42884,43001,43052,43073,43125,43268,43291,43330,43402,43549,43676,43869,43877,44009,44212,44298,44486,44534,44783,44988,45012,45043,45060,45223,45342,45437,45469,45496,45590,45605,45717,45745,45822,45988,45999,46155,46494,46572,46626,46760,47010,47174,47203,47472,47532,47715,47754,47799,48136,48240,48287,48836,48850,48932,48998,49119,49141,49519,49893,49957,50003,50027,50029,50135,50315,50352,50399,50598,50607,50680,50889,50957,50988,51269,51482,51548,51665,52062,52095,52187,52309,52374,52435,52539,52686,52720,52742,52777,52943,53201,53420,53451,53479,53589,53637,53639,53705,53834,53847,53896,53957,54081,54163,54270,54303,54377,54398,54543,54700,54723,54751,54980,55099,55330,55372,55445,55535,55635,55772,55918,55953,56131,56322,56391,56393,56517,56526,56657,56904,57034,57040,57086,57227,57384,57788,57938,58000,58008,58087,58190,58370,58460,58573,58798,58803,58812,58943,59076,59132,59157,59262,59418,59479,59481,60016,60032,60129,60137,60191,60323,60426,60557,60558,60590,60594,60597,60599,60652,60736,60952 |

## Audit events logged (35)

|          ts | device    | event_type       |   detection_score | risk_level   |
|------------:|:----------|:-----------------|------------------:|:-------------|
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |
| 1.79091e+09 | 127.0.0.1 | ANOMALY_DETECTED |          0.605941 | LOW          |

## What this does NOT demonstrate

- No physical Raspberry Pi, managed switch, or IP camera was used.
- No real-world attacker traffic — only benign locally-generated TCP connections.
- Precision, recall and F1 are not reported: real traffic has no ground-truth labels, so any such number would be fabricated.
- The live runtime exercised here performs capture, flow aggregation, detection (Isolation Forest fitted on a short live baseline) and trust updates only. Evidence generation runs but is not persisted, and peer consensus, the response state machine and the enforcement executor are NOT wired into this runtime. The `details` text of rows in `alerts.csv`/`audit.db` produced by earlier runs that says a response/enforcement layer 'runs separately' is inaccurate: no such layer was active.
- The detector was fitted on a handful of flows from a single loopback host, so its flagged flows are not meaningful detections; this run validates the capture-to-audit data path, nothing about detection quality.
- See docs/REAL_NETWORK_GUIDE.md for what a genuine physical HIL run would need.