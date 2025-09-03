import numpy as np
import pandas as pd


def compute_pulse_stats(df):
    """
    Compute frequency and duration of high and low flow pulses.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q']
        Should represent a single water year (or full dataset for all_years).

    Returns
    -------
    dict
        Keys:
        - freq_high_pulses
        - dur_high_mean
        - dur_high_max
        - freq_low_pulses
        - dur_low_mean
        - dur_low_max
    """
    flows = df["q"].astype(float).values

    # thresholds based on percentiles of this dataset
    high_thresh = np.percentile(flows, 75)
    low_thresh = np.percentile(flows, 25)

    high_events = (flows > high_thresh).astype(int)
    low_events = (flows < low_thresh).astype(int)

    high_durations = _event_durations(high_events)
    low_durations = _event_durations(low_events)

    return {
        "freq_high_pulses": len(high_durations),
        "dur_high_mean": np.mean(high_durations) if high_durations else 0,
        "dur_high_max": np.max(high_durations) if high_durations else 0,
        "freq_low_pulses": len(low_durations),
        "dur_low_mean": np.mean(low_durations) if low_durations else 0,
        "dur_low_max": np.max(low_durations) if low_durations else 0,
    }


def _event_durations(events):
    """Helper to calculate consecutive event durations from a binary array."""
    durations, count = [], 0
    for e in events:
        if e == 1:
            count += 1
        elif count > 0:
            durations.append(count)
            count = 0
    if count > 0:
        durations.append(count)
    return durations
