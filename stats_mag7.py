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
    Lam1, Tau2, Tau3, Tau4, AR1, Amplitude, Phase.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'q' (daily flows)

    Returns
    -------
    dict
        {
            "lam1": float,
            "tau2": float,
            "tau3": float,
            "tau4": float,
            "ar1": float,
            "amplitude": float,
            "phase": float
        }
    """
    flows = df["q"].values

    # --- L-moments ---
    l1, l2, t3, t4 = lmoments(flows)  # your lmoments function returns lam1, lam2, tau3, tau4
    lam1 = l1
    tau2 = l2 / l1 if l1 != 0 else np.nan
    tau3 = t3
    tau4 = t4

    # --- AR(1) ---
    if len(flows) > 1:
        ar1 = np.corrcoef(flows[:-1], flows[1:])[0,1]
    else:
        ar1 = np.nan

    # --- Amplitude & Phase ---
    # Use FFT for daily signal
    n = len(flows)
    fft_vals = np.fft.fft(flows - np.mean(flows))
    freqs = np.fft.fftfreq(n)
    # Annual frequency (~1 cycle per year)
    idx = np.argmin(np.abs(freqs - 1/365))
    amp = 2 * np.abs(fft_vals[idx]) / n
    ph = np.angle(fft_vals[idx])

    return {
        "mean_l_moment": lam1,
        "l_cv": tau2,
        "l_skew": tau3,
        "l_kurt": tau4,
        "ar1_coefficient": ar1,
        "amplitude": amp,
        "phase": ph
    }

