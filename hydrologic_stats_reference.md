# 📊 Hydrologic Statistics Reference

| **Category**        | **Statistic**            | **Column Name(s)**        | **Definition**                                                                 |
|----------------------|--------------------------|----------------------------|--------------------------------------------------------------------------------|
| **Magnitude**        | Mean Monthly Flow        | `mean_month_01` … `mean_month_12` | Average daily flow in each calendar month (Jan=01 … Dec=12).                   |
|                      | Median Monthly Flow      | `median_month_01` … `median_month_12` | Median daily flow in each month.                                               |
|                      | Annual Extremes (high)   | `max_1day`, `max_3day`, `max_7day`, `max_30day`, `max_90day` | Maximum moving-average flows across different window lengths.                  |
|                      | Annual Extremes (low)    | `min_1day`, `min_3day`, `min_7day`, `min_30day`, `min_90day` | Minimum moving-average flows across different window lengths.                  |
| **Frequency/Duration** | High Pulse Frequency    | `freq_high_pulses`         | Number of distinct events where flow exceeds the 75th percentile.              |
|                      | High Pulse Duration      | `dur_high_mean`, `dur_high_max` | Mean and maximum length of high-flow pulse events.                             |
|                      | Low Pulse Frequency      | `freq_low_pulses`          | Number of distinct events where flow falls below the 25th percentile.          |
|                      | Low Pulse Duration       | `dur_low_mean`, `dur_low_max` | Mean and maximum length of low-flow pulse events.                              |
| **Rate of Change**   | Rise Rate                | `rise_rate`                | Mean of all positive daily changes in flow (`q[t] - q[t-1] > 0`).              |
|                      | Fall Rate                | `fall_rate`                | Mean of all negative daily changes in flow (`q[t] - q[t-1] < 0`).              |
|                      | Number of Reversals      | `reversals`                | Number of times daily changes switch sign (from rise to fall or vice versa).   |
| **Timing**           | Day of Year Max Flow     | `doy_max`                  | Julian date (1–366) of the annual maximum daily flow.                          |
|                      | Day of Year Min Flow     | `doy_min`                  | Julian date of the annual minimum daily flow.                                  |
|                      | Center of Timing (CT)    | `center_of_timing`         | Flow-weighted mean day of year (when most of the flow volume occurs).          |
| **Magnificent 7** *(separate module)* | Mean Flow                  | `mag_mean`                 | Mean daily flow for the water year.                                            |
|                      | High-Flow Threshold      | `mag_high`                 | 90th percentile flow value.                                                    |
|                      | Low-Flow Threshold       | `mag_low`                  | 10th percentile flow value.                                                    |
|                      | High Pulse Frequency     | `freq_high`                | Number of days above the 90th percentile.                                      |
|                      | Low Pulse Frequency      | `freq_low`                 | Number of days below the 10th percentile.                                      |
|                      | High Pulse Durations     | `dur_high_avg`, `dur_high_max`, `dur_high_count` | Stats for consecutive days above 90th percentile.                            |
|                      | Low Pulse Durations      | `dur_low_avg`, `dur_low_max`, `dur_low_count` | Stats for consecutive days below 10th percentile.                            |

---

⚡ Notes:  
- `all_years` rows represent aggregate stats across the full dataset.  
- Percentile cutoffs differ slightly between **Magnificent 7** (90/10) vs **pulse stats** (75/25), following IHA convention.  
- Day of year (`doy_*`) values are based on water year indexing but reported as Julian day (Jan 1 = 1).  
