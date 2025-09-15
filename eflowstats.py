import pandas as pd
import numpy as np
from scipy.stats import skew

import stats_timing
# import computation functions from submodules
from stats_monthly import compute_monthly_stats
from stats_extremes import compute_extreme_stats
from stats_pulses import compute_pulse_stats, compute_pulse_rate_stats
from stats_rates import compute_rise_fall_stats
from stats_timing import compute_timing_stats
from stats_variability import compute_variability_stats
from stats_baseflow import compute_baseflow_index
from stats_colwell import compute_colwell_stats
from stats_frequency import compute_frequency_stats
from stats_mag7 import compute_mag7



class EflowStats:
    """
    Compute environmental flow statistics from daily streamflow records.

    This class ingests a CSV file containing daily streamflow data and computes a
    wide range of hydrologic indices, including monthly summaries, annual extremes,
    flow variability, baseflow, and event-based metrics such as pulses and rise/fall rates.

    Parameters
    ----------
    infile : str
        Path to input CSV with at least two columns:
        - 'datetime' : datetime-like values
        - 'q' : daily streamflow values (numeric)
    start_month : int, optional
        First month of the water year (default is 10 = October).
    exclude_ranges : list of tuple of (str or datetime, str or datetime), optional
        List of (start_date, end_date) ranges to exclude from analysis.
        Dates are inclusive. Default is None.

    Attributes
    ----------
    infile : str
        Path to input file.
    start_month : int
        Water year starting month.
    exclude_ranges : list
        List of date ranges excluded from analysis.
    df : pandas.DataFrame
        Cleaned input data with normalized datetime column.
    """

    def __init__(self, infile, start_month: int = 10, exclude_ranges=None):
        self.infile = infile
        self.start_month = start_month
        self.exclude_ranges = exclude_ranges or []
        self.df = self._load_data()

    def _load_data(self):
        df = pd.read_csv(self.infile)

        # Normalize datetime
        if "datetime" not in df.columns:
            raise ValueError("CSV must contain a 'datetime' column.")
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce").dt.tz_localize(None)
        df = df.dropna(subset=["datetime"])

        # Rename flow column to "q"
        if "q" not in df.columns:
            raise ValueError("CSV must contain a 'q' column.")

        # Normalize to daily resolution (drop h:m:s)
        df["datetime"] = df["datetime"].dt.normalize()
        df = df.sort_values("datetime").reset_index(drop=True)
        return df

    def _water_year(self, dates):
        """Compute water year index for a datetime series."""
        return np.where(dates.dt.month >= self.start_month,
                        dates.dt.year + 1, dates.dt.year)

    def _apply_exclusions(self, df):
        """Remove user-specified date ranges from dataframe."""
        for (start, end) in self.exclude_ranges:
            start, end = pd.to_datetime(start), pd.to_datetime(end)
            df = df[~df["datetime"].between(start, end)]
        return df

    def _check_completeness(self, df):
        """
        Validate completeness of each water year.
        Excludes years with missing dates or NaN q values.
        Prints details of excluded years.
        """
        df = df.copy()
        df["water_year"] = self._water_year(df["datetime"])
        kept_years = []
        excluded = []

        for wy, g in df.groupby("water_year"):
            start = pd.Timestamp(year=wy - 1, month=self.start_month, day=1)
            end = pd.Timestamp(year=wy, month=self.start_month, day=1) - pd.Timedelta(days=1)

            expected = pd.date_range(start, end, freq="D")
            present = g["datetime"].unique()
            missing = expected.difference(present)
            nan_q = g["q"].isna().sum()

            if len(missing) > 0 or nan_q > 0:
                print(f"\n⚠ Excluding incomplete water year {wy}:")
                if len(missing) > 0:
                    self._print_missing_ranges(missing)
                if nan_q > 0:
                    print(f"   Missing q values: {nan_q}")
                excluded.append(wy)
            else:
                kept_years.append(wy)

        df = df[df["water_year"].isin(kept_years)]
        return df, kept_years, excluded

    def _print_missing_ranges(self, missing_dates):
        """Pretty-print consecutive missing date ranges."""
        s = pd.Series(missing_dates).sort_values()
        groups = (s.diff().dt.days != 1).cumsum()
        for _, block in s.groupby(groups):
            start, end = block.min().date(), block.max().date()
            if start == end:
                print(f"   Missing date: {start}")
            else:
                print(f"   Missing date range: {start} → {end}")


    def magnificent_seven(self):
        """
        Compute the updated 'Magnificent Seven' hydrologic indicators.

        These now include:
        - lam1: mean L-moment
        - tau2, tau3, tau4: L-CV, L-skew, L-kurt
        - ar1: lag-1 autocorrelation coefficient
        - amplitude: seasonal amplitude
        - phase: seasonal phase

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing:
            - 'water_year' : int or 'all_years'
            - Magnificent 7 flow statistics
        """
        df = self._apply_exclusions(self.df)
        df, kept_years, excluded = self._check_completeness(df)

        results = []
        for wy, g in df.groupby("water_year"):
            stats = compute_mag7(g)
            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate across all years ---
        if results:
            all_stats = compute_mag7(df)
            all_stats["water_year"] = "all_years"
            results.insert(0, all_stats)

        # --- Format DataFrame ---
        df_out = pd.DataFrame(results)
        cols = ["water_year"] + [c for c in df_out.columns if c != "water_year"]
        df_out = df_out[cols]
        df_out.loc[1:] = df_out.loc[1:].sort_values("water_year")

        return df_out


    def HIAP_stats(self, use_median=False):
        """
        Compute HIAP metrics (Henriksen et al., 2006) in a format consistent with all_stats/mag7 outputs.

        Parameters
        ----------
        use_median : bool
            Aggregate per-year metrics using median if True, otherwise mean.

        Returns
        -------
        pandas.DataFrame
            One row per water year plus an aggregated 'all_years' row.
        """
        df = self._apply_exclusions(self.df)
        df, kept_years, excluded = self._check_completeness(df)

        results = []

        # --- Compute per-year metrics ---
        for wy, g in df.groupby("water_year"):
            stats = {}

            # Ma1: mean daily flow
            stats["Ma1"] = g["q"].mean()

            # Ma3: CV per year (std/mean)
            stats["Ma3"] = g["q"].std(ddof=1) / g["q"].mean() if g["q"].mean() != 0 else np.nan

            # Ml17: min 7-day moving average / mean annual flow
            min_7day = g["q"].rolling(7, min_periods=1).mean().min()
            mean_annual = g["q"].mean()
            stats["Ml17"] = min_7day / mean_annual if mean_annual != 0 else np.nan

            # Fl1: low pulse count (25th percentile of full record)
            low_thresh = np.percentile(df["q"], 25)
            pulses = compute_pulse_stats(g, low_thresh=low_thresh, high_thresh=np.inf)
            stats["Fl1"] = pulses["low_pulse_count"]

            # Fh1: high pulse count (75th percentile of full record)
            high_thresh = np.percentile(df["q"], 75)
            pulses = compute_pulse_stats(g, low_thresh=-np.inf, high_thresh=high_thresh)
            stats["Fh1"] = pulses["high_pulse_count"]

            # Fh5: flood frequency (median of full record)
            median_thresh = np.median(df["q"])
            pulses = compute_pulse_stats(g, low_thresh=-np.inf, high_thresh=median_thresh)
            stats["Fh5"] = pulses["high_pulse_count"]

            # Tl2: variability of Julian date of annual minima (per-year is NaN)
            stats["Tl2"] = np.nan

            # Th1: Julian date of annual maximum
            timing_stats = compute_timing_stats(g)
            stats["Th1"] = timing_stats.get("julian_max", np.nan)

            # Dh2: maximum 3-day moving average
            stats["Dh2"] = g["q"].rolling(3, min_periods=1).mean().max()

            # Ta2, Ta3, Phase (per-year NaN)
            stats["Ta2"] = np.nan
            stats["Ta3"] = np.nan
            stats["Phase"] = np.nan

            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate all-years metrics ---
        df_all = df.copy()
        stats_all = {}

        # Ma1
        stats_all["Ma1"] = df_all["q"].mean()

        # Ma3: mean/median of annual CVs
        yearly_cvs = df_all.groupby("water_year")["q"].agg(
            lambda x: x.std(ddof=1) / x.mean() if x.mean() != 0 else np.nan)
        stats_all["Ma3"] = yearly_cvs.median() if use_median else yearly_cvs.mean()

        # Ml17
        min7_over_mean = df_all.groupby("water_year").apply(
            lambda x: x["q"].rolling(7, min_periods=1).mean().min() / x["q"].mean() if x["q"].mean() != 0 else np.nan
        )
        stats_all["Ml17"] = min7_over_mean.median() if use_median else min7_over_mean.mean()

        # Fl1, Fh1, Fh5
        low_thresh = np.percentile(df_all["q"], 25)
        high_thresh = np.percentile(df_all["q"], 75)
        median_thresh = np.median(df_all["q"])

        fl1_per_year = df_all.groupby("water_year").apply(
            lambda x: compute_pulse_stats(x, low_thresh=low_thresh, high_thresh=np.inf)["low_pulse_count"]
        )
        fh1_per_year = df_all.groupby("water_year").apply(
            lambda x: compute_pulse_stats(x, low_thresh=-np.inf, high_thresh=high_thresh)["high_pulse_count"]
        )
        fh5_per_year = df_all.groupby("water_year").apply(
            lambda x: compute_pulse_stats(x, low_thresh=-np.inf, high_thresh=median_thresh)["high_pulse_count"]
        )

        stats_all["Fl1"] = fl1_per_year.median() if use_median else fl1_per_year.mean()
        stats_all["Fh1"] = fh1_per_year.median() if use_median else fh1_per_year.mean()
        stats_all["Fh5"] = fh5_per_year.median() if use_median else fh5_per_year.mean()

        # Ta2: Colwell predictability
        stats_all["Ta2"] = compute_colwell_stats(df_all).get("colwell_predictability", np.nan)

        # Ta3: seasonal predictability of flooding
        flood_thresh = df_all["q"].quantile(1 - 1 / 1.67)
        df_all["month_bin"] = ((df_all["datetime"].dt.month - 1) // 2) + 1
        flood_matrix = df_all[df_all["q"] > flood_thresh].groupby("month_bin")["q"].count()
        stats_all["Ta3"] = flood_matrix.max() / flood_matrix.sum() if flood_matrix.sum() > 0 else np.nan

        # Tl2 & Th1 using CV of Julian min/max
        timing_all = df_all.groupby("water_year").apply(compute_timing_stats)
        julian_mins = timing_all.apply(lambda x: x["julian_min"])
        julian_maxs = timing_all.apply(lambda x: x["julian_max"])

        stats_all["Tl2"] = (julian_mins.std(ddof=1) / julian_mins.mean()) * 100 if julian_mins.mean() != 0 else np.nan
        stats_all["Th1"] = (julian_maxs.std(ddof=1) / julian_maxs.mean()) * 100 if julian_maxs.mean() != 0 else np.nan

        # Phase from MAG7
        stats_all["Phase"] = compute_mag7(df_all)["phase"]

        # Dh2
        dh2_per_year = df_all.groupby("water_year").apply(lambda x: x["q"].rolling(3, min_periods=1).mean().max())
        stats_all["Dh2"] = dh2_per_year.median() if use_median else dh2_per_year.mean()

        stats_all["water_year"] = "all_years"
        results.insert(0, stats_all)

        # --- Format DataFrame ---
        df_out = pd.DataFrame(results)
        cols = ["water_year"] + [c for c in df_out.columns if c != "water_year"]
        df_out = df_out[cols]
        df_out.loc[1:] = df_out.loc[1:].sort_values("water_year")

        return df_out


    def all_stats(self):
        """
        Compute extended flow statistics for each water year and overall.

        Includes:
        - Magnificent 7 core indicators (mean, 90th, 10th percentile, skew, CV, timing, Colwell)
        - Monthly means/medians
        - Annual extreme magnitudes (1, 3, 7, 30, 90 day)
        - Pulse frequencies/durations (high/low)
        - Average rise/fall rates during high and low pulses
        - General rise/fall rates and reversals
        - Timing of extremes (Julian dates of min/max, center of timing)
        - Variability (coefficient of variation, standard deviation)
        - Baseflow index

        Returns
        -------
        pandas.DataFrame
            A DataFrame with one row per water year plus an aggregated "all_years" row.
            Columns include water_year and all computed hydrologic statistics.
        """
        df = self._apply_exclusions(self.df)
        df, kept_years, excluded = self._check_completeness(df)

        results = []
        for wy, g in df.groupby("water_year"):
            stats = {}

            # --- Magnificent Seven metrics ---
            stats.update(compute_mag7(g))

            # --- Monthly stats ---
            stats.update(compute_monthly_stats(g))

            # --- Extremes ---
            stats.update(compute_extreme_stats(g))

            # --- Pulses ---
            pulse_stats = compute_pulse_stats(g)
            stats.update(pulse_stats)

            # --- Pulse rise/fall rates ---
            pulse_rate_stats = compute_pulse_rate_stats(
                g,
                high_thresh=pulse_stats["high_thresh_used"],
                low_thresh=pulse_stats["low_thresh_used"]
            )
            stats.update(pulse_rate_stats)

            # --- Rise/Fall rates ---
            rise_fall_stats = compute_rise_fall_stats(g)
            stats.update(rise_fall_stats)

            # --- Timing ---
            stats.update(compute_timing_stats(g))

            # --- Variability ---
            stats.update(compute_variability_stats(g))

            # --- Baseflow ---
            stats.update(compute_baseflow_index(g))

            # --- Colwell ---
            stats.update(compute_colwell_stats(g))

            # --- Frequency stats ---
            stats.update(compute_frequency_stats(g))

            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate across all years ---
        if results:
            df_all = df.copy()
            stats_all = {}

            # --- Magnificent Seven metrics ---
            stats_all.update(compute_mag7(df_all))

            # --- Monthly stats ---
            stats_all.update(compute_monthly_stats(df_all))

            # --- Extreme stats ---
            stats_all.update(compute_extreme_stats(df_all))

            # --- Pulse stats ---
            pulse_stats_all = compute_pulse_stats(df_all)
            stats_all.update(pulse_stats_all)

            # --- Pulse rise/fall rates ---
            pulse_rate_stats_all = compute_pulse_rate_stats(
                df_all,
                high_thresh=pulse_stats_all["high_thresh_used"],
                low_thresh=pulse_stats_all["low_thresh_used"]
            )
            stats_all.update(pulse_rate_stats_all)

            # --- Rise/Fall rates ---
            rise_fall_stats_all = compute_rise_fall_stats(df_all)
            stats_all.update(rise_fall_stats_all)

            # --- Timing stats ---
            stats_all.update(compute_timing_stats(df_all))

            # --- Variability stats ---
            stats_all.update(compute_variability_stats(df_all))

            # --- Baseflow index ---
            stats_all.update(compute_baseflow_index(df_all))

            # --- Colwell stats ---
            stats_all.update(compute_colwell_stats(df_all))

            # --- Frequency stats ---
            stats_all.update(compute_frequency_stats(df_all))

            # --- Compute CV of Julian min/max across valid water years ---
            julian_max_by_year = [s["julian_max"] for s in results if s.get("julian_max") is not None]
            julian_min_by_year = [s["julian_min"] for s in results if s.get("julian_min") is not None]

            stats_all["cv_julian_max"] = (
                np.std(julian_max_by_year, ddof=1) / np.mean(julian_max_by_year)
                if len(julian_max_by_year) > 1 else np.nan
            )
            stats_all["cv_julian_min"] = (
                np.std(julian_min_by_year, ddof=1) / np.mean(julian_min_by_year)
                if len(julian_min_by_year) > 1 else np.nan
            )

            # --- Normalize count-type metrics per water year ---
            COUNT_METRICS = ["high_pulse_count", "low_pulse_count", "reversals"]
            n_years = len(kept_years)
            for metric in COUNT_METRICS:
                if metric in stats_all:
                    stats_all[metric] /= n_years

            stats_all["water_year"] = "all_years"
            results.insert(0, stats_all)

        # --- Format output ---
        df_out = pd.DataFrame(results)
        cols = ["water_year"] + [c for c in df_out.columns if c != "water_year"]
        df_out = df_out[cols]
        df_out.loc[1:] = df_out.loc[1:].sort_values("water_year")

        return df_out


    def save_stats(self, df, outfile):
        """
        Save computed statistics to CSV.

        Parameters
        ----------
        df : pandas.DataFrame
           DataFrame of hydrologic statistics (e.g., from all_stats()).
        outfile : str
           Path to output CSV file.

        Returns
        -------
        pandas.DataFrame
           The same DataFrame passed in, for chaining.
        """
        df.to_csv(outfile, index=False)
        print(f"\n✅ Stats saved to {outfile}")
        return df

