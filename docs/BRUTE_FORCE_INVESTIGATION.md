# Brute-force recall investigation (auto-generated)

SYNTHETIC data. Seeds: [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]. Single-attack scenarios (attack_types=[X]) so each attack is isolated. Mean ± std over seeds. Detector/simulator unmodified.

## Q1/Q2 Recall at the training-quantile-0.99 threshold vs ranking quality (AUC), and ramp-up

| intensity | attack | recall | recall_sd | auc | auc_sd | r_first10 | r_after10 |
|---|---|---|---|---|---|---|---|
| high | brute_force | 0.670 | 0.195 | 0.983 | 0.009 | 0.694 | 0.665 |
| high | exfiltration | 0.375 | 0.184 | 0.973 | 0.013 | 0.546 | 0.340 |
| high | port_scan | 0.999 | 0.000 | 0.999 | 0.000 | 0.997 | 1.000 |
| high | protocol_irregularity | 0.958 | 0.049 | 0.997 | 0.001 | 0.937 | 0.963 |
| high | traffic_spike | 0.209 | 0.286 | 0.971 | 0.017 | 0.220 | 0.207 |
| low | brute_force | 0.670 | 0.202 | 0.983 | 0.010 | 0.660 | 0.672 |
| low | exfiltration | 0.931 | 0.058 | 0.995 | 0.002 | 0.965 | 0.924 |
| low | port_scan | 0.999 | 0.001 | 0.999 | 0.000 | 0.993 | 1.000 |
| low | protocol_irregularity | 0.940 | 0.045 | 0.997 | 0.001 | 0.894 | 0.948 |
| low | traffic_spike | 0.013 | 0.020 | 0.923 | 0.013 | 0.010 | 0.013 |


## Threshold sensitivity (recall / FPR on normal flows at training-score quantiles)

| intensity | attack | recall_q0.9 | recall_q0.95 | recall_q0.99 | recall_q0.999 | fpr_q0.9 | fpr_q0.95 | fpr_q0.99 | fpr_q0.999 |
|---|---|---|---|---|---|---|---|---|---|
| high | brute_force | 1.000 | 0.833 | 0.670 | 0.221 | 0.102 | 0.050 | 0.010 | 0.001 |
| high | exfiltration | 0.962 | 0.822 | 0.375 | 0.009 | 0.101 | 0.050 | 0.011 | 0.001 |
| high | port_scan | 1.000 | 1.000 | 0.999 | 0.851 | 0.103 | 0.051 | 0.011 | 0.001 |
| high | protocol_irregularity | 1.000 | 0.999 | 0.958 | 0.575 | 0.102 | 0.051 | 0.011 | 0.001 |
| high | traffic_spike | 0.998 | 0.794 | 0.209 | 0.006 | 0.101 | 0.050 | 0.010 | 0.001 |
| low | brute_force | 1.000 | 0.823 | 0.670 | 0.209 | 0.103 | 0.050 | 0.011 | 0.001 |
| low | exfiltration | 1.000 | 0.999 | 0.931 | 0.051 | 0.102 | 0.049 | 0.011 | 0.001 |
| low | port_scan | 1.000 | 1.000 | 0.999 | 0.849 | 0.103 | 0.051 | 0.011 | 0.001 |
| low | protocol_irregularity | 1.000 | 0.999 | 0.940 | 0.559 | 0.102 | 0.051 | 0.011 | 0.001 |
| low | traffic_spike | 0.802 | 0.123 | 0.013 | 0.001 | 0.100 | 0.050 | 0.011 | 0.001 |


## Q3 Recall by attacked device type (NaN = never attacked in those seeds)

| intensity | attack | recall_camera | recall_plc | recall_sensor |
|---|---|---|---|---|
| high | brute_force | 1.000 | 0.822 | 0.211 |
| high | exfiltration | 0.338 | 0.277 | 0.513 |
| high | port_scan | 1.000 | 0.999 | 0.999 |
| high | protocol_irregularity | 1.000 | 0.964 | 0.913 |
| high | traffic_spike | 0.005 | 0.319 | 0.640 |
| low | brute_force | 1.000 | 0.826 | 0.207 |
| low | exfiltration | 0.988 | 0.928 | 0.874 |
| low | port_scan | 1.000 | 0.999 | 0.998 |
| low | protocol_irregularity | 0.994 | 0.935 | 0.890 |
| low | traffic_spike | 0.004 | 0.031 | 0.000 |


## Q4 What is in the training-score tail that sets the threshold?

| index | mean over seeds |
|---|---|
| n_train | 10655.300 |
| n_tail | 107.000 |
| tail_frac_dns_ntp | 0.970 |
| all_frac_dns_ntp | 0.056 |
| tail_frac_cold_start | 0.002 |
| all_frac_cold_start | 0.006 |
| threshold | 0.657 |


## Brute-force flow feature medians vs baseline medians (same device type)

| intensity | device_type | bf_conn_freq | base_conn_freq | bf_failed_ratio | base_failed_ratio | bf_dest_diversity | base_dest_diversity | bf_dport_diversity | base_dport_diversity | bf_src_dst_freq | base_src_dst_freq | bf_byte_rate | base_byte_rate | bf_packet_rate | base_packet_rate | bf_duration_s | base_duration_s | bf_pkt_rate_dev | base_pkt_rate_dev | bf_byte_rate_dev | base_byte_rate_dev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high | camera | 49.000 | 11.000 | 0.892 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 49.000 | 10.000 | 2023.033 | 69593.010 | 23.083 | 59.733 | 0.346 | 0.998 | -8.277 | 0.000 | -26.933 | 0.000 |
| high | plc | 49.000 | 6.000 | 0.899 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 49.000 | 5.000 | 2026.299 | 6751.963 | 23.216 | 57.943 | 0.347 | 0.197 | -3.050 | 0.000 | -4.487 | 0.000 |
| high | sensor | 49.000 | 3.000 | 0.895 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 49.000 | 2.000 | 2032.090 | 2902.745 | 23.058 | 27.860 | 0.348 | 0.289 | -0.766 | 0.000 | -1.672 | 0.000 |
| low | camera | 15.000 | 11.000 | 0.891 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 15.000 | 10.000 | 1983.257 | 69593.010 | 22.233 | 59.733 | 0.355 | 0.998 | -8.451 | 0.000 | -27.229 | 0.000 |
| low | plc | 15.000 | 6.000 | 0.892 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 15.000 | 5.000 | 2024.983 | 6751.963 | 22.685 | 57.943 | 0.356 | 0.197 | -3.120 | 0.000 | -4.473 | 0.000 |
| low | sensor | 15.000 | 3.000 | 0.909 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 15.000 | 2.000 | 1989.477 | 2902.745 | 22.388 | 27.860 | 0.353 | 0.289 | -0.895 | 0.000 | -1.615 | 0.000 |


## Q5 Mean SHAP contribution toward anomalous (path-length units), top 6 per attack (all attack flows)

| attack | feature | mean_contribution |
|---|---|---|
| brute_force | failed_ratio | 1.461 |
| port_scan | failed_ratio | 1.255 |
| brute_force | burst_indicator | 0.758 |
| brute_force | byte_rate_dev | 0.704 |
| port_scan | burst_indicator | 0.644 |
| port_scan | log_bytes | 0.635 |
| port_scan | byte_rate_dev | 0.581 |
| brute_force | pkt_rate_dev | 0.578 |
| port_scan | log_packets | 0.562 |
| port_scan | dest_diversity | 0.549 |
| brute_force | log_bytes | 0.520 |
| brute_force | packet_rate | 0.362 |


## Q6 Evidence corroboration: device-type baseline vs service-level baseline (high intensity)

| mode | kind | n | corroborated_rate | mean_strength |
|---|---|---|---|---|
| device_type_baseline | attack | 34203 | 1.000 | 0.941 |
| device_type_baseline | false_positive | 3301 | 0.993 | 0.912 |
| service_baseline | attack | 34203 | 1.000 | 0.941 |
| service_baseline | false_positive | 3301 | 0.455 | 0.282 |
