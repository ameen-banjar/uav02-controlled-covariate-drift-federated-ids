# UAV-02 confirmatory run manifest

- Frozen commit/tag: [('0a201c80ed6f09919b2650b6ec9fac38bc455d6d', 'uav02-confirmatory-freeze-v1')] (consistent across seeds: True)
- Execution: parallel; measured peak concurrent seed processes = 3. seeds launched as separate OS processes via `xargs -P 3` (up to 3 concurrent on one machine); each process has its own RNG state (torch/numpy seeded per run) and writes only seed-prefixed files
- Hardware: Apple M1, 8 logical CPUs; backend ['mps']
- Environment: {'python': '3.11.4', 'torch': '2.10.0', 'numpy': '1.26.4', 'pandas': '2.3.3', 'scikit-learn': '1.7.2', 'scipy': '1.16.3', 'matplotlib': '3.10.7'}
- Compiled post hoc (see script docstring); start times after a seed's first run are derived.

| seed | algorithm | schedule | start (DERIVED/INFERRED, not measured) | end (file mtime) | wall s | complete |
|---|---|---|---|---|---|---|
| 21 | fedavg | none | 2026-09-25T01:21:28+03:00 | 2026-09-25T01:58:28+03:00 | 2220 | True |
| 21 | fedavg | sudden | 2026-09-25T01:58:28+03:00 | 2026-09-25T02:25:14+03:00 | 1606 | True |
| 21 | fedavg | gradual | 2026-09-25T02:25:14+03:00 | 2026-09-25T02:51:58+03:00 | 1604 | True |
| 21 | fedavg | recurring | 2026-09-25T02:51:58+03:00 | 2026-09-25T03:18:28+03:00 | 1590 | True |
| 21 | fedprox | none | 2026-09-25T03:18:28+03:00 | 2026-09-25T03:46:23+03:00 | 1675 | True |
| 21 | fedprox | sudden | 2026-09-25T03:46:23+03:00 | 2026-09-25T04:13:58+03:00 | 1655 | True |
| 21 | fedprox | gradual | 2026-09-25T04:13:58+03:00 | 2026-09-25T04:42:03+03:00 | 1685 | True |
| 21 | fedprox | recurring | 2026-09-25T04:42:03+03:00 | 2026-09-25T09:56:31+03:00 | 18868 | True |
| 32 | fedavg | none | 2026-09-25T01:21:28+03:00 | 2026-09-25T01:58:09+03:00 | 2201 | True |
| 32 | fedavg | sudden | 2026-09-25T01:58:09+03:00 | 2026-09-25T02:24:40+03:00 | 1591 | True |
| 32 | fedavg | gradual | 2026-09-25T02:24:40+03:00 | 2026-09-25T02:51:12+03:00 | 1592 | True |
| 32 | fedavg | recurring | 2026-09-25T02:51:12+03:00 | 2026-09-25T03:17:28+03:00 | 1575 | True |
| 32 | fedprox | none | 2026-09-25T03:17:28+03:00 | 2026-09-25T03:45:10+03:00 | 1663 | True |
| 32 | fedprox | sudden | 2026-09-25T03:45:10+03:00 | 2026-09-25T04:12:34+03:00 | 1644 | True |
| 32 | fedprox | gradual | 2026-09-25T04:12:34+03:00 | 2026-09-25T04:40:30+03:00 | 1676 | True |
| 32 | fedprox | recurring | 2026-09-25T04:40:30+03:00 | 2026-09-25T09:55:01+03:00 | 18871 | True |
| 43 | fedavg | none | 2026-09-25T01:21:28+03:00 | 2026-09-25T01:58:09+03:00 | 2202 | True |
| 43 | fedavg | sudden | 2026-09-25T01:58:09+03:00 | 2026-09-25T02:24:37+03:00 | 1587 | True |
| 43 | fedavg | gradual | 2026-09-25T02:24:37+03:00 | 2026-09-25T02:51:17+03:00 | 1600 | True |
| 43 | fedavg | recurring | 2026-09-25T02:51:17+03:00 | 2026-09-25T03:17:39+03:00 | 1582 | True |
| 43 | fedprox | none | 2026-09-25T03:17:39+03:00 | 2026-09-25T03:45:18+03:00 | 1659 | True |
| 43 | fedprox | sudden | 2026-09-25T03:45:18+03:00 | 2026-09-25T04:12:37+03:00 | 1639 | True |
| 43 | fedprox | gradual | 2026-09-25T04:12:37+03:00 | 2026-09-25T04:40:27+03:00 | 1670 | True |
| 43 | fedprox | recurring | 2026-09-25T04:40:27+03:00 | 2026-09-25T09:54:58+03:00 | 18871 | True |
| 54 | fedavg | none | 2026-09-25T09:55:03+03:00 | 2026-09-25T10:10:16+03:00 | 913 | True |
| 54 | fedavg | sudden | 2026-09-25T10:10:16+03:00 | 2026-09-25T10:23:43+03:00 | 806 | True |
| 54 | fedavg | gradual | 2026-09-25T10:23:43+03:00 | 2026-09-25T10:40:53+03:00 | 1030 | True |
| 54 | fedavg | recurring | 2026-09-25T10:40:53+03:00 | 2026-09-25T10:55:30+03:00 | 877 | True |
| 54 | fedprox | none | 2026-09-25T10:55:30+03:00 | 2026-09-25T11:10:47+03:00 | 918 | True |
| 54 | fedprox | sudden | 2026-09-25T11:10:47+03:00 | 2026-09-25T11:25:03+03:00 | 856 | True |
| 54 | fedprox | gradual | 2026-09-25T11:25:03+03:00 | 2026-09-25T11:40:40+03:00 | 936 | True |
| 54 | fedprox | recurring | 2026-09-25T11:40:40+03:00 | 2026-09-25T12:00:22+03:00 | 1183 | True |
| 65 | fedavg | none | 2026-09-25T09:55:05+03:00 | 2026-09-25T10:10:20+03:00 | 915 | True |
| 65 | fedavg | sudden | 2026-09-25T10:10:20+03:00 | 2026-09-25T10:23:51+03:00 | 811 | True |
| 65 | fedavg | gradual | 2026-09-25T10:23:51+03:00 | 2026-09-25T10:41:19+03:00 | 1048 | True |
| 65 | fedavg | recurring | 2026-09-25T10:41:19+03:00 | 2026-09-25T10:55:56+03:00 | 876 | True |
| 65 | fedprox | none | 2026-09-25T10:55:56+03:00 | 2026-09-25T11:11:09+03:00 | 913 | True |
| 65 | fedprox | sudden | 2026-09-25T11:11:09+03:00 | 2026-09-25T11:25:30+03:00 | 862 | True |
| 65 | fedprox | gradual | 2026-09-25T11:25:30+03:00 | 2026-09-25T11:41:38+03:00 | 968 | True |
| 65 | fedprox | recurring | 2026-09-25T11:41:38+03:00 | 2026-09-25T12:01:21+03:00 | 1183 | True |