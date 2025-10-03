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
- `phase (depreciated, see Mag7)`  
  Flow-weighted timing angle of the hydrograph (radians or degrees).  
- `amplitude (depreciated, see Mag7)`  
  Magnitude of seasonal variation in daily flow.

---

### 7. **Variability Statistics**
From `compute_variability_stats`

- `std_daily`  
  Standard deviation of daily streamflow.  
- `cv_daily`  
  Coefficient of variation of daily streamflow (std / mean).  
- `cv_annual`  
  Interannual coefficient of variation (std of annual means / mean of annual means).

---

### 8. **Baseflow Statistics**
From `compute_baseflow_index`

- `bfi`  
  Ratio of baseflow to total flow, estimated via a recursive digital filter.

---

### 9. **Colwell Predictability Metrics**
From `compute_colwell_stats`

- `colwell_constancy`  
  Measure of uniformity in daily flow.  
- `colwell_contingency`  
  Measure of seasonal predictability.  
- `colwell_predictability`  
  Sum of constancy and contingency, overall flow predictability.

---

## 🌟 Magnificent 7 Indicators (Mag7)
The **Magnificent 7 (Mag7)** metrics are computed by `all_stats()` and represent key annual hydrologic characteristics.  

| Metric | Column Name | Description |
|--------|------------|-------------|
| Mean flow (λ₁) | `lam1` | Average daily flow for the water year. |
| L-CV (τ₂) | `tau2` | L-moment coefficient of variation. |
| L-skew (τ₃) | `tau3` | L-moment skewness. |
| L-kurtosis (τ₄) | `tau4` | L-moment kurtosis. |
| AR(1) coefficient | `ar1` | Lag-1 autocorrelation of daily flows. |
| Amplitude | `amplitude` | Magnitude of seasonal variation. |
| Phase | `phase` | Timing of peak seasonal flow (radians/degrees). |

---

## 🔹 HIAP (Henriksen et al., 2006) Statistics
The **HIAP_stats** function computes a suite of hydrologic indices based on Henriksen et al. 2006 methodology. The naming conventions align with `py_flowstats` for consistency.  

| HIAP Stat | Existing in py_flowstats? | Column Name | Notes |
|------------|--------------------------|-------------|-------|
| Ma1 | Yes | `mag_mean` | Mean of daily flows over the entire record. |
| Ma3 | Partially | `cv_annual` | Mean (or median) of per-year CVs of daily flows. |
| Ml17 | Partially | `min_7day_ratio` | Ratio of 7-day minimum to mean annual flow per year; aggregate mean/median. |
| Fl1 | Yes | `low_pulse_count` | Low pulse frequency (≤ 25th percentile). |
| Fh1 | Yes | `high_pulse_count` | High pulse frequency (≥ 75th percentile). |
| Fh5 | Yes | `fh5` | Flood frequency above median flow. |
| Ta2 | Yes | `colwell_predictability` | Predictability metric from Colwell analysis. |
| Ta3 | Yes | `ta3` | Seasonal predictability of flooding (max flood days / total flood days). |
| Tl2 | Yes | `cv_julian_min` | Variability in timing of annual minima. |
| Th1 | Yes | `julian_max` | Timing of annual maximum flow. |
| Phase | Yes | `phase` | Flow-weighted timing of hydrograph. |
| Dh2 | Yes | `max_3day_mean` | Annual maximum 3-day moving average; aggregate mean/median. |

**Notes:**

- For `Ma3`, `Ml17`, and `Dh2`, HIAP_stats computes per-year statistics and then aggregates using **mean or median** based on user preference.  
- Column names were chosen to match `py_flowstats` naming conventions where possible (`mag_mean`, `cv_annual`, `julian_max`, etc.).  
- HIAP_stats returns a `pandas.DataFrame` formatted identically to `all_stats()`, with per-water-year rows and an aggregated `all_years` row.

---

## 📦 Output

- All statistics (Mag7 and HIAP) are computed **per water year** and summarized into an `all_years` row.  
- Output is returned as a `pandas.DataFrame` ready for further analysis or CSV export.

