# Drift validity report: td (time dilation), s = 1

Time-dilation transform at full strength (s = 1, c = 1.6): times x 1.6, time-derived rates / 1.6, IP-row Rate only.

Rows checked: 245,526. Flags raised: **0**.

## 1. Meaning of each edited feature

| Feature | Holds | Source | Flag |
|---|---|---|---|
| `IAT` | time since the previous packet, seconds | Feature_extraction.py, IAT = time_interval (IP) or ts - previous_11_time (802.11) | ok |
| `flow_active_time` | last minus first timestamp of the packet's flow, seconds | Supporting_functions.py, get_flow_info() | ok |
| `std_duration` | standard deviation of the flow's packet timestamps, seconds | Supporting_functions.py, get_flow_info(), np.std(duration) | ok |
| `Srate` | source-to-destination packets of the flow divided by the flow duration | Feature_extraction.py, srate = src_to_dst_pkt / flow_duration | ok |
| `Drate` | destination-to-source packets of the flow divided by the flow duration | Feature_extraction.py, drate = dst_to_src_pkt / flow_duration | ok |
| `Rate` | IP packets: payload bits divided by the inter-packet interval, Mb/s. 802.11 packets: radiotap PHY rate x payload size / packet size, no timing term | Connectivity_features.py get_data_rate(); Communication_features.py calculate_packet_size() | ok |

## 2. Rows leaving the physical domain

| Feature | Row type | Domain | Rows leaving | Share of all rows | Share of that row type |
|---|---|---|---:|---:|---:|
| `IAT` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `flow_active_time` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `std_duration` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Srate` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Drate` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Rate` | all | [0, inf] | 0 | 0.0% | 0.0% |

## 3. Rate x time relations tied by the extractor

| Relation | Row type | Median factor after transform | Rows changed | Flag |
|---|---|---:|---:|---|
| Srate x flow_active_time | all | 1.0000 | 0 | kept |
| Drate x flow_active_time | all | 1.0000 | 0 | kept |
| Rate x IAT | ip | 1.0000 | 0 | kept |

## 4. Consistency with the stated intent (uniform re-timing)

| Feature | Row type | Role | Expected factor | Median factor | Flag |
|---|---|---|---:|---:|---|
| `IAT` | all | time | 1.6000 | 1.6000 | ok |
| `flow_active_time` | all | time | 1.6000 | 1.6000 | ok |
| `std_duration` | all | time | 1.6000 | 1.6000 | ok |
| `Srate` | all | rate | 0.6250 | 0.6250 | ok |
| `Drate` | all | rate | 0.6250 | 0.6250 | ok |
| `Rate` | ip | rate | 0.6250 | 0.6250 | ok |
