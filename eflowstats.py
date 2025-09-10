import pandas as pd
import numpy as np
from scipy.stats import skew

# import computation functions from submodules
from stats_monthly import compute_monthly_stats
from stats_extremes import compute_extreme_stats
from stats_pulses import compute_pulse_stats, compute_pulse_rate_stats
from stats_rates import compute_rise_fall_stats
from stats_timing import compute_timing_stats
from stats_variability import compute_variability_stats
from stats_baseflow import compute_baseflow_index
from stats_colwell import compute_colwell_stats


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
        Compute the 'Magnificent Seven' hydrologic indicators.

        These include:
        - Mean daily flow
        - High-flow quantile (90th percentile)
        - Low-flow quantile (10th percentile)
        - Skewness of daily flows
        - Intra-annual coefficient of variation (CV)
        - Julian day of annual maximum flow
        - Colwell predictability metrics (constancy, contingency, predictability)

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
            stats = {}

            # --- Core Magnificent 7 metrics ---
            stats["mag_mean"] = g["q"].mean()
            stats["mag_high"] = g["q"].quantile(0.9)
            stats["mag_low"] = g["q"].quantile(0.1)
            stats["mag_skew"] = skew(g["q"], bias=False)

            # --- CV ---
            stats.update(compute_variability_stats(g))

            # --- Timing of max flow ---
            timing_stats = compute_timing_stats(g)
            stats["julian_max"] = timing_stats.get("julian_max", None)

            # --- Colwell metrics ---
            stats.update(compute_colwell_stats(g))

            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate across all years ---
        if results:
            all_stats = {}

            all_stats["mag_mean"] = df["q"].mean()
            all_stats["mag_high"] = df["q"].quantile(0.9)
            all_stats["mag_low"] = df["q"].quantile(0.1)
            all_stats["mag_skew"] = skew(df["q"], bias=False)

            all_stats.update(compute_variability_stats(df))

            timing_stats_all = compute_timing_stats(df)
            all_stats["julian_max"] = timing_stats_all.get("julian_max", None)

            all_stats.update(compute_colwell_stats(df))

            all_stats["water_year"] = "all_years"
            results.insert(0, all_stats)

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

            # --- Magnificent Seven core metrics ---
            stats["mag_mean"] = g["q"].mean()
            stats["mag_high"] = g["q"].quantile(0.9)
            stats["mag_low"] = g["q"].quantile(0.1)
            stats["mag_skew"] = skew(g["q"], bias=False)

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

            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate across all years ---
        if results:
            df_all = df.copy()
            stats_all = {}

            # --- Magnificent Seven core metrics ---
            stats_all["mag_mean"] = df_all["q"].mean()
            stats_all["mag_high"] = df_all["q"].quantile(0.9)
            stats_all["mag_low"] = df_all["q"].quantile(0.1)
            stats_all["mag_skew"] = skew(df_all["q"], bias=False)

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

