# Hydrologic Statistics Reference

This reference describes the hydrologic indices currently implemented in the Python version of **eflowstats**.

---

## 📘 General

- **Water year handling**  
  Water years are calculated relative to the `start_month` parameter (default: October = 10).  
  Incomplete water years (missing dates or NaN flows) are excluded.

- **Exclusion ranges**  
  Users may specify custom date ranges to omit from calculations.

---

## 📊 Statistics by Module

### 1. **Monthly Statistics**
From `compute_monthly_stats`

- `mean_month_01` ... `mean_month_12`  
  Mean daily flow for each month.
- `median_month_01` ... `median_month_12`  
  Median daily flow for each month.

---

### 2. **Extreme Magnitude Statistics**
From `compute_extreme_stats`

- `max_1day`, `max_3day`, `max_7day`, `max_30day`, `max_90day`  
  Annual maximum moving averages.
- `min_1day`, `min_3day`, `min_7day`, `min_30day`, `min_90day`  
  Annual minimum moving averages.

---

### 3. **Pulse Frequency & Duration**
From `compute_pulse_stats`

- `high_pulse_count`  
  Number of high flow pulses (≥ 75th percentile).  
- `high_pulse_avg_dur`  
  Mean duration (days) of high flow pulses.  
- `low_pulse_count`  
  Number of low flow pulses (≤ 25th percentile).  
- `low_pulse_avg_dur`  
  Mean duration (days) of low flow pulses.  
- `high_thresh_used`, `low_thresh_used`  
  Threshold values applied.

---

### 4. **Pulse Rise/Fall Rates**
From `compute_pulse_rate_stats`

- `high_pulse_rise_mean`  
  Mean daily rise rate within high flow pulses.  
- `high_pulse_fall_mean`  
  Mean daily fall rate within high flow pulses.  
- `low_pulse_rise_mean`  
  Mean daily rise rate within low flow pulses.  
- `low_pulse_fall_mean`  
  Mean daily fall rate within low flow pulses.  

---

### 5. **General Rise/Fall Statistics**
From `compute_rise_fall_stats`

- `mean_rise_rate`  
  Mean positive daily change in flow.  
- `mean_fall_rate`  
  Mean negative daily change in flow.  
- `reversals`  
  Number of reversals (changes from rise → fall or fall → rise).

---

### 6. **Timing Statistics**
From `compute_timing_stats` and `all_stats`

- `julian_min`  
  Julian day of minimum daily flow.  
- `julian_max`  
  Julian day of maximum daily flow.  
- `center_of_timing`  
  Weighted center of timing of annual flows.  
- `cv_julian_min` *(all_years only)*  
  Coefficient of variation of Julian dates of annual minima.  
- `cv_julian_max` *(all_years only)*  
  Coefficient of variation of Julian dates of annual maxima.  

---

### 7. **Variability Statistics**
From `compute_variability_stats`

- `std_dev`  
  Standard deviation of daily streamflow.  
- `cv_daily`  
  Coefficient of variation of daily streamflow (std / mean).  
- `cv_annual`  
  Interannual coefficient of variation (std of annual means / mean of annual means).

---

### 8. **Baseflow Statistics**
From `compute_baseflow_index`

- `baseflow_index`  
  Ratio of baseflow to total flow, estimated via a recursive digital filter.

---

## 📦 Output
- Statistics are computed **per water year** and aggregated into an `all_years` summary.  
- `cv_julian_min` and `cv_julian_max` appear **only in the all_years row**.  
- Output is returned as a `pandas.DataFrame` and can be saved to CSV via `.save_stats()`.