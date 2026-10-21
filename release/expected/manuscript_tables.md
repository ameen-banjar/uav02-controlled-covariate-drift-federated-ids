# Manuscript reference values (extracted from manuscript.md; do not edit by hand)

**Table 2.**

| Schedule | Positive-strength rounds | Full-strength rounds | Post-removal intervals |
|---|---|---|---|
| None | None | None | Clean reference throughout |
| Sudden | 15–29 | 15–29 (15 rounds) | 30–45 |
| Gradual | 11–34 | 20–25 (6 rounds) | 35–45 |
| Recurring | 15–21 and 30–36 | 15–21 and 30–36 (14 rounds) | 22–29 and 37–45 |

**Table 3.**

| Algorithm | Schedule | Metric | Mean | SD | Range | 95% t interval | d_z | Negative seeds |
|---|---|---|---:|---:|---|---|---:|---:|
| FedAvg | Sudden | macro-F1 | -0.0120 | 0.0102 | [-0.0221, +0.0042] | [-0.0247, +0.0007] | -1.17 | 4/5 |
| FedAvg | Sudden | Regular recall | -0.0114 | 0.0036 | [-0.0157, -0.0061] | [-0.0159, -0.0069] | -3.15 | 5/5 |
| FedAvg | Gradual | macro-F1 | -0.0122 | 0.0104 | [-0.0204, +0.0054] | [-0.0251, +0.0008] | -1.17 | 4/5 |
| FedAvg | Gradual | Regular recall | -0.0107 | 0.0034 | [-0.0152, -0.0061] | [-0.0148, -0.0065] | -3.17 | 5/5 |
| FedAvg | Recurring | macro-F1 | -0.0183 | 0.0105 | [-0.0245, +0.0004] | [-0.0314, -0.0052] | -1.74 | 4/5 |
| FedAvg | Recurring | Regular recall | -0.0434 | 0.0265 | [-0.0858, -0.0186] | [-0.0763, -0.0104] | -1.64 | 5/5 |
| FedProx | Sudden | macro-F1 | -0.0255 | 0.0085 | [-0.0316, -0.0137] | [-0.0361, -0.0150] | -3.01 | 5/5 |
| FedProx | Sudden | Regular recall | -0.0201 | 0.0122 | [-0.0392, -0.0094] | [-0.0353, -0.0049] | -1.64 | 5/5 |
| FedProx | Gradual | macro-F1 | -0.0280 | 0.0086 | [-0.0361, -0.0163] | [-0.0387, -0.0173] | -3.25 | 5/5 |
| FedProx | Gradual | Regular recall | -0.0178 | 0.0101 | [-0.0329, -0.0069] | [-0.0303, -0.0052] | -1.76 | 5/5 |
| FedProx | Recurring | macro-F1 | -0.0323 | 0.0082 | [-0.0449, -0.0231] | [-0.0424, -0.0221] | -3.95 | 5/5 |
| FedProx | Recurring | Regular recall | -0.0674 | 0.0407 | [-0.1215, -0.0248] | [-0.1179, -0.0169] | -1.66 | 5/5 |

**Table 4.**

| Algorithm | Schedule / interval | Round | Mean | SD | Range | Descriptive 95% t interval |
|---|---|---:|---:|---:|---|---|
| FedAvg | Sudden / 30–45 | 45 | +0.0000 | 0.0023 | [−0.0024, +0.0039] | [−0.0029, +0.0029] |
| FedAvg | Gradual / 35–45 | 45 | +0.0022 | 0.0072 | [−0.0061, +0.0134] | [−0.0067, +0.0112] |
| FedAvg | Recurring / 22–29 | 29 | +0.0009 | 0.0037 | [−0.0055, +0.0038] | [−0.0037, +0.0055] |
| FedAvg | Recurring / 37–45 | 45 | +0.0008 | 0.0035 | [−0.0026, +0.0066] | [−0.0035, +0.0051] |
| FedProx | Sudden / 30–45 | 45 | −0.0017 | 0.0031 | [−0.0067, +0.0005] | [−0.0055, +0.0021] |
| FedProx | Gradual / 35–45 | 45 | −0.0014 | 0.0030 | [−0.0063, +0.0011] | [−0.0052, +0.0023] |
| FedProx | Recurring / 22–29 | 29 | −0.0007 | 0.0015 | [−0.0024, +0.0011] | [−0.0025, +0.0011] |
| FedProx | Recurring / 37–45 | 45 | −0.0010 | 0.0014 | [−0.0035, +0.0001] | [−0.0028, +0.0008] |

**Table 5.**

| Algorithm | True class → MITM | Mean | SD | Range | Descriptive 95% t interval | d_z |
|---|---|---:|---:|---|---|---:|
| FedAvg | Regular | +0.0245 | 0.0114 | [+0.0116, +0.0414] | [+0.0103, +0.0387] | +2.15 |
| FedAvg | Video | +0.4404 | 0.0473 | [+0.3751, +0.4978] | [+0.3817, +0.4990] | +9.32 |
| FedProx | Regular | +0.0393 | 0.0229 | [+0.0170, +0.0719] | [+0.0108, +0.0677] | +1.71 |
| FedProx | Video | +0.4815 | 0.0912 | [+0.3884, +0.5950] | [+0.3683, +0.5948] | +5.28 |

**Table 6.**

| Algorithm | Schedule | Δ macro-F1 test (10 classes) | Δ macro-F1 test (9 classes) | Δ macro-F1 validation | Δ Regular recall test | Δ Regular recall validation | Residual macro-F1 r45 test |
|---|---|---:|---:|---:|---:|---:|---:|
| FedAvg | Sudden | −0.0722 | −0.0797 | −0.0124 | −0.0150 | −0.0131 | −0.0006 |
| FedAvg | Gradual | −0.0763 | −0.0845 | −0.0126 | −0.0130 | −0.0109 | +0.0017 |
| FedAvg | Recurring | −0.0875 | −0.0969 | −0.0206 | −0.0519 | −0.0498 | +0.0004 |
| FedProx | Sudden | −0.0750 | −0.0833 | −0.0248 | −0.0246 | −0.0228 | −0.0021 |
| FedProx | Gradual | −0.0836 | −0.0928 | −0.0296 | −0.0198 | −0.0179 | −0.0022 |
| FedProx | Recurring | −0.0910 | −0.1011 | −0.0330 | −0.0752 | −0.0738 | −0.0019 |

## In-text values

- L2 FedAvg: +0.0056, +0.0046, +0.0026
- L2 FedProx: +0.0071, +0.0043, +0.0024
- H1 FedAvg: -3.3409, 0.4271, -3.9119, -2.9258, -3.8712, -2.8105, -7.82
- H1 FedProx: -3.1385, 0.5091, -3.8601, -2.6337, -3.7706, -2.5063, -6.16
- H1 drops FedAvg: -1.4452, -4.7861
- H1 drops FedProx: -1.4878, -4.6263
