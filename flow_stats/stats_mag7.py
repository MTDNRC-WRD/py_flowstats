import pandas as pd
import numpy as np
from scipy.stats import linregress

def lmoments(data, nmom=4):
    """
    Efficient L-moment calculation (λ1, τ2, τ3, τ4).
    Works well for daily hydrologic series up to 50k+ values.

    Parameters
    ----------
    data : array-like
        Input data (streamflows).
    nmom : int
        Number of L-moments to compute (max 4 supported).

    Returns
    -------
    dict
        {"lam1", "tau2", "tau3", "tau4"}
    """
    x = np.sort(np.asarray(data, dtype=float))
    n = len(x)
    if n < 4:
        return {"lam1": np.nan, "tau2": np.nan, "tau3": np.nan, "tau4": np.nan}

    # Compute probability-weighted moments (PWMs)
    i = np.arange(1, n+1)  # ranks
    b0 = np.mean(x)
    b1 = np.sum((i-1)/(n-1) * x) / n
    b2 = np.sum(((i-1)*(i-2))/((n-1)*(n-2)) * x) / n
    b3 = np.sum(((i-1)*(i-2)*(i-3))/((n-1)*(n-2)*(n-3)) * x) / n

    # Convert PWMs -> L-moments
    lam1 = b0
    lam2 = 2*b1 - b0
    lam3 = 6*b2 - 6*b1 + b0
    lam4 = 20*b3 - 30*b2 + 12*b1 - b0

    tau2 = lam2 / lam1 if lam1 != 0 else np.nan
    tau3 = lam3 / lam2 if lam2 != 0 else np.nan
    tau4 = lam4 / lam2 if lam2 != 0 else np.nan

    return {
        "lam1": lam1,
        "tau2": tau2,
        "tau3": tau3,
        "tau4": tau4,
    }


def compute_mag7(df):
    """
    Compute Magnificent 7 hydrologic indicators:
    Lam1, Tau2, Tau3, Tau4, AR1, Amplitude, Phase (in Julian days).

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'q' (daily flows) and 'datetime'

    Returns
    -------
    dict
        {
            "mean_l_moment": float,
            "l_cv": float,
            "l_skew": float,
            "l_kurt": float,
            "ar1_coefficient": float,
            "amplitude": float,
            "phase": float  # in Julian days
        }
    """
    flows = df["q"].values
    n = len(flows)

    # --- L-moments ---
    lm = lmoments(flows)
    lam1 = lm["lam1"]
    tau2 = lm["tau2"]
    tau3 = lm["tau3"]
    tau4 = lm["tau4"]

    # --- AR(1) ---
    if n > 1:
        ar1 = np.corrcoef(flows[:-1], flows[1:])[0, 1]
    else:
        ar1 = np.nan

    # --- Amplitude & Phase ---
    if n > 0:
        fft_vals = np.fft.fft(flows - np.mean(flows))
        freqs = np.fft.fftfreq(n)
        # Annual frequency (~1 cycle per 365 days)
        idx = np.argmin(np.abs(freqs - 1 / 365))
        amp = 2 * np.abs(fft_vals[idx]) / n
        ph_rad = np.angle(fft_vals[idx])
        # Convert phase from radians to Julian day
        phase_doy = (ph_rad / (2 * np.pi)) * 365
        # Ensure positive day-of-year
        if phase_doy < 0:
            phase_doy += 365
    else:
        amp = np.nan
        phase_doy = np.nan

    return {
        "mean_l_moment": lam1,
        "l_cv": tau2,
        "l_skew": tau3,
        "l_kurt": tau4,
        "ar1_coefficient": ar1,
        "amplitude": amp,
        "phase": phase_doy,
    }

