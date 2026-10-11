"""Builds the three supporting datasets (energy, rainfall, crop) so they line up with the
existing Kaggle solar data (Plant 1/2, 15-min, 15 May - 17 Jun 2020).
NOTE: these are SIMULATED, physically-motivated datasets (no internet source was available).
To use real data, replace the CSVs in /data keeping the same column names."""
import os, numpy as np, pandas as pd
_B = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(_B, "data") if os.path.isdir(os.path.join(_B, "data")) else _B   # works with or without a data/ folder
rng = np.random.default_rng(42)

# crop: (opt temp C, opt seasonal rain mm, opt pH, opt N kg/ha, base yield t/ha)
CROPS = {"Rice": (27, 1200, 6.0, 100, 4.5), "Maize": (25, 700, 6.3, 120, 5.5),
         "Tomato": (24, 700, 6.4, 130, 25.0), "Chilli": (27, 800, 6.3, 90, 3.0),
         "Okra": (29, 700, 6.5, 100, 10.0), "Banana": (27, 1500, 6.2, 200, 30.0),
         "Cassava": (27, 1200, 5.8, 80, 20.0), "Groundnut": (28, 600, 6.2, 25, 2.2),
         "Cowpea": (28, 500, 6.3, 20, 1.3)}

def energy():
    w = pd.read_csv(f"{DATA}/Plant_1_Weather_Sensor_Data.csv", usecols=["DATE_TIME", "AMBIENT_TEMPERATURE"])
    w["DATE_TIME"] = pd.to_datetime(w["DATE_TIME"]); w = w.set_index("DATE_TIME")
    idx = pd.date_range(w.index.min(), w.index.max(), freq="15min")
    t = w.reindex(idx).interpolate()["AMBIENT_TEMPERATURE"]
    h = idx.hour + idx.minute / 60; wk = idx.dayofweek >= 5
    g = lambda c, s: np.exp(-((h - c) ** 2) / (2 * s ** 2))
    load = (0.25 + 0.55 * g(7, 1.2) + 0.95 * g(20, 1.8) + (0.25 + 0.25 * wk) * g(13, 2.5)
            + 0.09 * np.clip(t - 24, 0, None) * (0.4 + g(15, 4)) + 0.12 * wk)
    load = np.clip(0.5 * load * rng.normal(1, 0.08, len(idx)), 0.05, None)
    pd.DataFrame({"DATE_TIME": idx, "AMBIENT_TEMPERATURE": t.values.round(2),
                  "IS_WEEKEND": wk.astype(int), "HOUSEHOLD_LOAD_KW": load.round(3)}).to_csv(f"{DATA}/household_energy_consumption.csv", index=False)

def rainfall():  # Kerala-like monsoon climate, daily, 2015-2024
    mm = np.array([12, 18, 40, 110, 260, 650, 590, 350, 260, 300, 180, 50.])
    days = pd.date_range("2015-01-01", "2024-12-31"); rain = np.zeros(len(days)); prev = 0
    for i, d in enumerate(days):
        m = mm[d.month - 1] * rng.normal(1, 0.25); depth = 8 + m / 40
        p = np.clip(m / (30 * depth), 0.02, 0.92) * (1.5 if prev > 0 else 0.7)
        rain[i] = 0.8 * rng.gamma(0.8, depth / 0.8) if rng.random() < min(p, 0.95) else 0; prev = rain[i]
    doy = days.dayofyear.values
    temp = 28.5 + 2.5 * np.sin(2 * np.pi * (doy - 60) / 365) - 0.02 * rain.clip(0, 60) + rng.normal(0, .6, len(days))
    hum = np.clip(72 + 10 * np.sin(2 * np.pi * (doy - 120) / 365) + 0.15 * rain.clip(0, 80) + rng.normal(0, 3, len(days)), 45, 99)
    pd.DataFrame({"DATE": days, "RAINFALL_MM": rain.round(1), "TEMPERATURE_C": temp.round(1),
                  "HUMIDITY_PCT": hum.round(1)}).to_csv(f"{DATA}/rainfall_daily.csv", index=False)

def crops(n=4500):
    rows = []
    for _ in range(n):
        c = rng.choice(list(CROPS)); T0, R0, P0, N0, Y0 = CROPS[c]
        T, R, H = rng.uniform(18, 36), rng.uniform(200, 2200), rng.uniform(45, 95)
        P, N = rng.uniform(4.5, 8.0), rng.uniform(10, 260)
        f = (np.exp(-((T - T0) / 4.5) ** 2 / 2) * np.exp(-((np.log(R / R0)) / 0.55) ** 2 / 2)
             * np.exp(-((P - P0) / 1.0) ** 2 / 2) * (0.4 + 0.6 * np.exp(-((N - N0) / 80) ** 2 / 2))
             * (0.85 + 0.15 * H / 95))
        rows.append([c, round(R), round(T, 1), round(H), round(P, 2), round(N), round(max(Y0 * f * rng.normal(1, .07), 0), 2)])
    pd.DataFrame(rows, columns=["crop", "rainfall_mm", "temperature_c", "humidity_pct", "soil_ph",
                                "nitrogen_kg_ha", "yield_t_ha"]).to_csv(f"{DATA}/crop_yield.csv", index=False)

if __name__ == "__main__":
    energy(); rainfall(); crops(); print("Datasets written to", DATA)
