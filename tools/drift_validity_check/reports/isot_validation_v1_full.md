# Drift validity report: v1 (first campaign), s = 1

First-campaign transform at full strength (s = 1): rates x 0.4, times and `Duration` x 1.6, Entropy - 0.5 floored at the 5th percentile of the untransformed Entropy. Stated intent: slower traffic timing.

Rows checked: 245,526. Flags raised: **11**.

## 1. Meaning of each edited feature

| Feature | Holds | Source | Flag |
|---|---|---|---|
| `Rate` | IP packets: payload bits divided by the inter-packet interval, Mb/s. 802.11 packets: radiotap PHY rate x payload size / packet size, no timing term | Connectivity_features.py get_data_rate(); Communication_features.py calculate_packet_size() | ok |
| `Srate` | source-to-destination packets of the flow divided by the flow duration | Feature_extraction.py, srate = src_to_dst_pkt / flow_duration | ok |
| `Drate` | destination-to-source packets of the flow divided by the flow duration | Feature_extraction.py, drate = dst_to_src_pkt / flow_duration | ok |
| `IAT` | time since the previous packet, seconds | Feature_extraction.py, IAT = time_interval (IP) or ts - previous_11_time (802.11) | ok |
| `flow_active_time` | last minus first timestamp of the packet's flow, seconds | Supporting_functions.py, get_flow_info() | ok |
| `Duration` | IP time-to-live on IP packets; 0 on 802.11 packets | Connectivity_features.py, Connectivity_features_time.duration() returns packet.ttl | NAME DOES NOT MATCH |
| `Entropy` | Shannon entropy of the payload bytes, bits | Supporting_functions.py, calculate_entropy() | ok |

## 2. Rows leaving the physical domain

| Feature | Row type | Domain | Rows leaving | Share of all rows | Share of that row type |
|---|---|---|---:|---:|---:|
| `Rate` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Srate` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Drate` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `IAT` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `flow_active_time` | all | [0, inf] | 0 | 0.0% | 0.0% |
| `Duration` | ip | [0, 255] | 196,163 | 79.9% | 79.9% |
| `Entropy` | all | [0, 8] | 0 | 0.0% | 0.0% |

## 3. Rate x time relations tied by the extractor

| Relation | Row type | Median factor after transform | Rows changed | Flag |
|---|---|---:|---:|---|
| Srate x flow_active_time | all | 0.6400 | 207,006 | BROKEN |
| Drate x flow_active_time | all | 0.6400 | 148,199 | BROKEN |
| Rate x IAT | ip | 0.6400 | 245,267 | BROKEN |

## 4. Consistency with the stated intent (uniform re-timing)

| Feature | Row type | Role | Expected factor | Median factor | Flag |
|---|---|---|---:|---:|---|
| `IAT` | all | time | 1.6000 | 1.6000 | ok |
| `flow_active_time` | all | time | 1.6000 | 1.6000 | ok |
| `std_duration` | all | time | 1.6000 | 1.0000 | MISMATCH |
| `Srate` | all | rate | 0.6250 | 0.4000 | MISMATCH |
| `Drate` | all | rate | 0.6250 | 0.4000 | MISMATCH |
| `Rate` | ip | rate | 0.6250 | 0.4000 | MISMATCH |
| `Duration` | all | none | 1.0000 | n/a | MISMATCH |
| `Entropy` | all | none | 1.0000 | n/a | MISMATCH |
