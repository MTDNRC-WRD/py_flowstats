import pandas as pd

# read csv
df = pd.read_csv(r"C:\Users\CND367\Downloads\georgetownlake_elevation_trainingdata.csv", parse_dates=["datetime"])

# make sure month/year exist
df["year"] = df["datetime"].dt.year
df["month"] = df["datetime"].dt.month

# === Step 1: fill eom for each month ===
eom_lookup = (
    df.dropna(subset=["eom_elevation"])
      .groupby(["year", "month"])["eom_elevation"]
      .first()
)

df["eom_filled"] = df.set_index(["year", "month"]).index.map(eom_lookup)

# === Step 2: compute last month's eom ===
# shift the eom_lookup by 1 month within each year
eom_lookup_lagged = (
    eom_lookup.rename("eom")
    .reset_index()
    .assign(month_shifted=lambda d: d["month"] + 1)
)

# handle year rollover (Dec -> Jan)
eom_lookup_lagged.loc[eom_lookup_lagged["month_shifted"] == 13, "month_shifted"] = 1
eom_lookup_lagged["year_shifted"] = eom_lookup_lagged["year"]
eom_lookup_lagged.loc[eom_lookup_lagged["month_shifted"] == 1, "year_shifted"] += 1

# lookup dict: (year, month) → last month’s eom
lm_lookup = dict(
    zip(
        zip(eom_lookup_lagged["year_shifted"], eom_lookup_lagged["month_shifted"]),
        eom_lookup_lagged["eom"]
    )
)

# map into df
df["lm_filled"] = df.set_index(["year", "month"]).index.map(lm_lookup)

df.to_csv(r"C:\Users\CND367\Downloads\georgetownlake_elevation_trainingdata_cleaned_bm_em.csv")

print(df.head())