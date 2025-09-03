import numpy as np

def compute_magnificent7(flows):
    """
    Compute the 'Magnificent Seven' hydrologic indicators.
    flows : 1D numpy array or pandas Series of daily flows (single water year)
    """
    mag_mean = np.mean(flows)
    mag_high = np.percentile(flows, 90)
    mag_low = np.percentile(flows, 10)

    high_events = (flows > mag_high).astype(int)
    low_events = (flows < mag_low).astype(int)

    freq_high = high_events.sum()
    freq_low = low_events.sum()

    dur_high = _event_durations(high_events)
    dur_low = _event_durations(low_events)

    return {
        "mag_mean": mag_mean,
        "mag_high": mag_high,
        "mag_low": mag_low,
        "freq_high": freq_high,
        "freq_low": freq_low,
        "dur_high_avg": np.mean(dur_high) if dur_high else 0,
        "dur_high_max": np.max(dur_high) if dur_high else 0,
        "dur_high_count": len(dur_high),
        "dur_low_avg": np.mean(dur_low) if dur_low else 0,
        "dur_low_max": np.max(dur_low) if dur_low else 0,
        "dur_low_count": len(dur_low),
    }

def _event_durations(events):
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
