import pandas as pd
import numpy as np

# import computation functions from submodules
from stats_magnificent7 import compute_magnificent7
from stats_monthly import compute_monthly_stats
from stats_extremes import compute_extreme_stats
from stats_pulses import compute_pulse_stats
from stats_rates import compute_rise_fall_stats
from stats_timing import compute_timing_stats


class EflowStats:
    def __init__(self, infile, start_month: int = 10, exclude_ranges=None):
        """
        Parameters
        ----------
        infile : str
            Path to input CSV with columns: datetime, q
        start_month : int
            Start month of water year (default: 10 = October)
        exclude_ranges : list of tuples
            [(start_date, end_date), ...] to exclude from analysis
        """
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
        Returns DataFrame of stats per year and 'all_years'.
        """
        df = self._apply_exclusions(self.df)
        df, kept_years, excluded = self._check_completeness(df)

        results = []
        for wy, g in df.groupby("water_year"):
            stats = compute_magnificent7(g["q"].values)
            stats["water_year"] = wy
            results.append(stats)

        if results:
            all_years = compute_magnificent7(df["q"].values)
            all_years["water_year"] = "all_years"
            results.insert(0, all_years)

        df_out = pd.DataFrame(results)
        cols = ["water_year"] + [c for c in df_out.columns if c != "water_year"]
        df_out = df_out[cols]
        df_out.loc[1:] = df_out.loc[1:].sort_values("water_year")
        return df_out

    def all_stats(self):
        """
        Compute extended flow statistics for each water year and overall.
        Includes:
        - Monthly means/medians
        - Annual extreme magnitudes (1, 3, 7, 30, 90 day)
        - Pulse frequencies/durations (high/low)
        - Rise/Fall rates and reversals
        - Timing (Julian dates of min/max, center of timing)
        """
        df = self._apply_exclusions(self.df)
        df, kept_years, excluded = self._check_completeness(df)

        results = []
        for wy, g in df.groupby("water_year"):
            stats = {}

            # --- Monthly stats ---
            stats.update(compute_monthly_stats(g))

            # --- Extremes ---
            stats.update(compute_extreme_stats(g))

            # --- Pulses ---
            stats.update(compute_pulse_stats(g))

            # --- Rise/Fall rates ---
            stats.update(compute_rise_fall_stats(g))

            # --- Timing ---
            stats.update(compute_timing_stats(g))

            stats["water_year"] = wy
            results.append(stats)

        # --- Aggregate across all years ---
        if results:
            df_all = df.copy()
            stats_all = {}
            stats_all.update(compute_monthly_stats(df_all))
            stats_all.update(compute_extreme_stats(df_all))
            stats_all.update(compute_pulse_stats(df_all))
            stats_all.update(compute_rise_fall_stats(df_all))
            stats_all.update(compute_timing_stats(df_all))
            stats_all["water_year"] = "all_years"
            results.insert(0, stats_all)

        # --- Format output ---
        df_out = pd.DataFrame(results)
        cols = ["water_year"] + [c for c in df_out.columns if c != "water_year"]
        df_out = df_out[cols]
        df_out.loc[1:] = df_out.loc[1:].sort_values("water_year")

        return df_out


    def save_stats(self, df, outfile):
        df.to_csv(outfile, index=False)
        print(f"\n✅ Stats saved to {outfile}")
        return df

