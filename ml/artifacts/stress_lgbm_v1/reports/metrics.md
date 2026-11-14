# Holdout metrics

| Model | PR-AUC | ROC-AUC | Brier | Log-loss | n |
|---|---|---|---|---|---|
| B0 climatology | 0.1727 | 0.5393 | 0.1339 | 0.4412 | 79,524 |
| B1 logistic | 0.2004 | 0.5952 | 0.1334 | 0.4374 | 79,524 |
| LGBM raw | 0.2188 | 0.6536 | 0.1398 | 0.4516 | 79,524 |
| LGBM calibrated | 0.2192 | 0.6543 | 0.1357 | 0.4310 | 79,524 |

Holdout: **final** years [np.int64(2022), np.int64(2023), np.int64(2024), np.int64(2025)]; training years 2002-2021.
Shipped: **B1 logistic regression** (rule: LGBM-calibrated must beat B0 and B1 on PR-AUC and Brier).

## Cross-validation (out-of-fold, training years)

- LGBM calibrated (OOF): PR-AUC 0.3567, Brier 0.1122
- B1 logistic (OOF): PR-AUC 0.2612, Brier 0.1216

## Spatial check (every 5th 50-km block held out)

- held_out_family_unseen_cells: PR-AUC 0.2097, Brier 0.1448, n 13,649
- same_rows_full_model: PR-AUC 0.2093, Brier 0.1404, n 13,649

## By month (shipped model)

| Month | PR-AUC | Brier | base rate |
|---|---|---|---|
| 3 | 0.006 | 0.014 | 0.002 |
| 4 | 0.111 | 0.071 | 0.077 |
| 5 | 0.303 | 0.218 | 0.278 |
| 6 | 0.169 | 0.126 | 0.145 |
| 7 | 0.253 | 0.170 | 0.206 |
| 8 | 0.293 | 0.222 | 0.274 |
| 9 | 0.137 | 0.121 | 0.134 |
| 10 | 0.218 | 0.125 | 0.149 |

## By crop share (tercile)

- low: PR-AUC 0.161, base rate 0.145
- mid: PR-AUC 0.175, base rate 0.141
- high: PR-AUC 0.259, base rate 0.187

## Case study 2018 (year left out of training)

| Month | observed | predicted | usual year |
|---|---|---|---|
| 3 | 0.425 | 0.173 | 0.108 |
| 4 | 0.058 | 0.137 | 0.148 |
| 5 | 0.087 | 0.226 | 0.164 |
| 6 | 0.821 | 0.144 | 0.114 |
| 7 | 0.739 | 0.295 | 0.112 |
| 8 | 0.074 | 0.126 | 0.159 |
| 9 | 0.041 | 0.074 | 0.168 |
| 10 | 0.015 | 0.119 | 0.164 |

## Plain-language bands at 0.10 / 0.25 (holdout share)

- low: 0.369
- medium: 0.588
- high: 0.043

## Top features (mean gain)

- tmax_l1_z: 131,613
- t2m_l1_z: 68,877
- ndvi_z_l1: 61,160
- p_minus_et0_3m_l1_z: 55,581
- p_minus_et0_l1: 54,157
- dry_spell_max_l1: 43,630
- p_minus_et0_3m_l1: 41,581
- tmin_l1_z: 37,943
- gdd5_l1: 37,686
- clim_et0_m: 36,442
- p_minus_et0_l1_z: 33,393
- month_cos: 31,504
