"""Data loading, ML models and the recommendation engine for the AI-Powered Sustainable Home platform."""
import os, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from generate_datasets import CROPS

_B = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(_B, "data") if os.path.isdir(os.path.join(_B, "data")) else _B   # works with or without a data/ folder
SOLAR_FEATS = ["AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"]
GRID_CO2 = 0.71   # kg CO2 per kWh (approx. Indian grid emission factor)
STEP = 96         # 15-min steps per day

def _rf(**kw): return RandomForestRegressor(n_estimators=150, min_samples_leaf=2, n_jobs=-1, random_state=42, **kw)
def _metrics(y, p): return {"R2": r2_score(y, p), "MAE": mean_absolute_error(y, p), "RMSE": mean_squared_error(y, p) ** 0.5}
def _split(n, frac=0.8): return int(n * frac)

# ------------------------------------------------------------------ SOLAR
def load_solar(plant=1):
    g = pd.read_csv(f"{DATA}/Plant_{plant}_Generation_Data.csv", usecols=["DATE_TIME", "AC_POWER"])
    g["DATE_TIME"] = pd.to_datetime(g["DATE_TIME"], format="mixed", dayfirst=True)
    g = g.groupby("DATE_TIME", as_index=False)["AC_POWER"].mean()   # avg per-inverter AC kW (as in original dashboard)
    w = pd.read_csv(f"{DATA}/Plant_{plant}_Weather_Sensor_Data.csv", usecols=["DATE_TIME"] + SOLAR_FEATS)
    w["DATE_TIME"] = pd.to_datetime(w["DATE_TIME"])
    return g.merge(w, on="DATE_TIME").sort_values("DATE_TIME").reset_index(drop=True)

def train_solar(plant=1):
    df = load_solar(plant); k = _split(len(df))
    m = _rf().fit(df[SOLAR_FEATS][:k], df["AC_POWER"][:k])
    test = df.iloc[k:].copy(); test["PREDICTED"] = m.predict(test[SOLAR_FEATS])
    return {"model": m, "metrics": _metrics(test["AC_POWER"], test["PREDICTED"]), "test": test, "data": df,
            "importance": dict(zip(SOLAR_FEATS, m.feature_importances_))}

def to_home_kw(ac, ref, kwp):
    """Scale plant output to a rooftop system of `kwp` (85% performance ratio)."""
    return np.clip(np.asarray(ac) / ref.quantile(0.99) * kwp * 0.85, 0, kwp)

# ------------------------------------------------------------------ ENERGY
def load_energy():
    e = pd.read_csv(f"{DATA}/household_energy_consumption.csv", parse_dates=["DATE_TIME"])
    return e.set_index("DATE_TIME")

def _efeat(idx, temp, lag1d, prev_mean):
    return pd.DataFrame({"hour": idx.hour + idx.minute / 60, "dow": idx.dayofweek, "weekend": (idx.dayofweek >= 5).astype(int),
                         "temp": np.asarray(temp), "lag_1d": np.asarray(lag1d), "prev_day_mean": np.asarray(prev_mean)}, index=idx)

def train_energy():
    e = load_energy(); L = e["HOUSEHOLD_LOAD_KW"]
    dm = L.groupby(L.index.normalize()).mean()
    pm = pd.Series(L.index.normalize() - pd.Timedelta(days=1), index=L.index).map(dm)
    X = _efeat(L.index, e["AMBIENT_TEMPERATURE"], L.shift(STEP), pm).dropna(); y = L.loc[X.index]; k = _split(len(X), 0.75)
    m = _rf().fit(X[:k], y[:k]); test = pd.DataFrame({"ACTUAL": y[k:], "PREDICTED": m.predict(X[k:])})
    return {"model": m, "metrics": _metrics(test.ACTUAL, test.PREDICTED), "test": test, "data": e, "cols": list(X.columns)}

# ------------------------------------------------------------------ NEXT-DAY OUTLOOK (solar + load, persistence weather)
def next_day_outlook(S, E, plant, kwp):
    w = S["data"].set_index("DATE_TIME")[SOLAR_FEATS]
    full = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="15min")).interpolate().iloc[-STEP:]
    fidx = pd.date_range(full.index[-1] + pd.Timedelta(minutes=15), periods=STEP, freq="15min")
    fw = full.set_index(fidx)
    solar = to_home_kw(S["model"].predict(fw[SOLAR_FEATS]), S["data"]["AC_POWER"], kwp)
    L = E["data"]["HOUSEHOLD_LOAD_KW"].iloc[-STEP:]
    X = _efeat(fidx, E["data"]["AMBIENT_TEMPERATURE"].iloc[-STEP:], L.values, np.full(STEP, L.mean()))
    load = E["model"].predict(X[E["cols"]])
    return pd.DataFrame({"solar_kw": solar, "load_kw": load}, index=fidx)

def energy_balance(S, E, kwp):
    """Historical balance: measured plant AC (scaled to home size) vs household load."""
    d = S["data"].set_index("DATE_TIME")
    b = pd.DataFrame({"solar_kw": to_home_kw(d["AC_POWER"], d["AC_POWER"], kwp)}, index=d.index).join(
        E["data"][["HOUSEHOLD_LOAD_KW"]].rename(columns={"HOUSEHOLD_LOAD_KW": "load_kw"}), how="inner")
    return b

def self_use_with_battery(b, cap_kwh, eff=0.9):
    """15-min dispatch: solar serves load first, surplus charges the battery, battery covers later deficits."""
    soc = used = charged = 0.0; dt = 0.25
    for s, l in zip(b.solar_kw.values, b.load_kw.values):
        d = min(s, l); used += d * dt
        if cap_kwh > 0:
            ch = min((s - d) * dt, cap_kwh - soc); soc += ch; charged += ch
            take = min((l - d) * dt / eff, soc); soc -= take; used += take * eff
    return used, charged

def balance_kpis(b, tariff=7.0, battery=0.0):
    dt = 0.25; d = max(len(b) * dt / 24, 1); load = b.load_kw.sum() * dt; sol = b.solar_kw.sum() * dt; used, charged = self_use_with_battery(b, battery)
    return {"solar_kwh": sol, "load_kwh": load, "self_use_kwh": used, "self_sufficiency": used / load if load else 0,
            "export_kwh": max(np.clip(b.solar_kw - b.load_kw, 0, None).sum() * dt - charged, 0), "co2_saved_kg": used * GRID_CO2, "days": d,
            "bill_no_solar": load / d * 30 * tariff, "bill_with_solar": (load - used) / d * 30 * tariff, "saving_month": used / d * 30 * tariff}

# ------------------------------------------------------------------ WATER
def load_rain(): return pd.read_csv(f"{DATA}/rainfall_daily.csv", parse_dates=["DATE"]).set_index("DATE")

def train_rain():
    r = load_rain(); R = r["RAINFALL_MM"]; doy = r.index.dayofyear
    X = pd.DataFrame({"lag1": R.shift(1), "lag2": R.shift(2), "lag3": R.shift(3), "sum7": R.shift(1).rolling(7).sum(),
                      "doy_sin": np.sin(2 * np.pi * doy / 365), "doy_cos": np.cos(2 * np.pi * doy / 365),
                      "hum_lag1": r["HUMIDITY_PCT"].shift(1), "temp_lag1": r["TEMPERATURE_C"].shift(1)}, index=r.index).dropna()
    y = R.loc[X.index]; k = _split(len(X)); m = _rf().fit(X[:k], y[:k])
    test = pd.DataFrame({"ACTUAL": y[k:], "PREDICTED": m.predict(X[k:])})
    return {"model": m, "metrics": _metrics(test.ACTUAL, test.PREDICTED), "test": test, "data": r, "cols": list(X.columns), "X": X}

def simulate_tank(rain_mm, roof_m2, tank_l, persons, lpcd=135, nonpotable=0.5, runoff=0.8, extra_l=0):
    """Daily tank balance: harvested water covers the non-potable share of demand (flush, garden, laundry)."""
    demand = persons * lpcd * nonpotable + extra_l; s = tank_l * 0.3; out = []
    for mm in rain_mm:
        inflow = roof_m2 * mm * runoff; s += inflow; over = max(s - tank_l, 0); s -= over
        use = min(demand, s); s -= use; out.append((inflow, over, use, demand, s))
    return pd.DataFrame(out, index=rain_mm.index, columns=["harvest_l", "overflow_l", "supplied_l", "demand_l", "storage_l"])

def monthly_rain(r):
    yr = r.groupby([r.index.year, r.index.month])["RAINFALL_MM"].sum().groupby(level=1).mean()
    yr.index = pd.to_datetime(yr.index, format="%m").strftime("%b"); return yr

# ------------------------------------------------------------------ CROP
def train_crop():
    d = pd.read_csv(f"{DATA}/crop_yield.csv"); X = pd.concat([d.drop(columns=["crop", "yield_t_ha"]), pd.get_dummies(d["crop"]).astype(int)], axis=1)
    y = d["yield_t_ha"]; k = _split(len(d)); m = _rf().fit(X[:k], y[:k])
    p = m.predict(X[k:]); return {"model": m, "metrics": _metrics(y[k:], p), "cols": list(X.columns), "data": d,
                                  "test": pd.DataFrame({"ACTUAL": y[k:], "PREDICTED": p})}

def rank_crops(C, rain_mm, temp_c, hum, ph, n):
    rows = []
    for c in CROPS:
        row = {"rainfall_mm": rain_mm, "temperature_c": temp_c, "humidity_pct": hum, "soil_ph": ph, "nitrogen_kg_ha": n}
        row.update({k: int(k == c) for k in CROPS}); rows.append(row)
    X = pd.DataFrame(rows)[C["cols"]]; y = C["model"].predict(X)
    out = pd.DataFrame({"crop": list(CROPS), "predicted_yield_t_ha": y, "potential_%": [100 * v / CROPS[c][4] for c, v in zip(CROPS, y)]})
    return out.sort_values("predicted_yield_t_ha", ascending=False).reset_index(drop=True)

# ------------------------------------------------------------------ TRAIN ALL
def train_all():
    return {"solar": {1: train_solar(1), 2: train_solar(2)}, "energy": train_energy(), "rain": train_rain(), "crop": train_crop()}

# ------------------------------------------------------------------ PERSONALISED ANALYSIS
import copy
def appliance_table(rows):
    d = pd.DataFrame(rows, columns=["Appliance", "Watts", "Qty", "Hours", "Shiftable"]).fillna({"Watts": 0, "Qty": 0, "Hours": 0, "Shiftable": False})
    d["kWh_day"] = d.Watts * d.Qty * d.Hours / 1000; return d

def score(p, bk, tank, crop_row):
    items = [("Solar self-sufficiency", min(bk["self_sufficiency"] / 0.8, 1) * 25, 25),
             ("Electricity efficiency", float(np.clip((6 - bk["load_kwh"] / bk["days"] / p["persons"]) / 4, 0, 1)) * 15, 15),
             ("Rainwater supply", min(tank.supplied_l.sum() / max(tank.demand_l.sum(), 1), 1) * 20, 20),
             ("Water-use efficiency", float(np.clip((200 - p["lpcd"]) / 100, 0, 1)) * 10, 10)]
    if p["farm_m2"] > 0: items.append(("Crop suitability", min(crop_row["potential_%"] / 100, 1) * 30, 30))
    t = round(100 * sum(i[1] for i in items) / sum(i[2] for i in items))
    return {"total": t, "grade": "A" if t >= 80 else "B" if t >= 65 else "C" if t >= 50 else "D", "items": [(n, round(g, 1), m) for n, g, m in items]}

def analyze(M, plant, p):
    S, E, R, C = M["solar"][plant], M["energy"], M["rain"], M["crop"]; kwp = p["solar_kwp"]
    app = appliance_table(p["appliances"])
    daily = max(app.kWh_day.sum() if p["energy_source"] == "Appliance list" else p["monthly_units"] / 30, 0.5)
    f = daily / (E["data"]["HOUSEHOLD_LOAD_KW"].mean() * 24)          # scale ML load shape to the household's own demand
    bal = energy_balance(S, E, kwp); bal["load_kw"] = bal["load_kw"] * f
    out = next_day_outlook(S, E, plant, kwp); out["load_kw"] = out["load_kw"] * f
    bk = balance_kpis(bal, p["tariff"], p.get("battery_kwh", 0.0))
    tank = simulate_tank(R["data"].RAINFALL_MM["2024"], p["roof_m2"], p["tank_l"], p["persons"], p["lpcd"], p["nonpotable"] / 100, extra_l=p["garden_m2"] * p["irrig_l_m2"])
    monthly = monthly_rain(R["data"]); crops = rank_crops(C, p["season_rain"], p["temp_c"], p["humidity"], p["soil_ph"], p["nitrogen"])
    cur = crops[crops.crop == p["current_crop"]]; row = cur.iloc[0] if len(cur) else crops.iloc[0]
    rain_pred = float(R["model"].predict(R["X"].iloc[[-1]][R["cols"]])[0])
    a = dict(bal=bal, bk=bk, outlook=out, tank=tank, monthly=monthly, crops=crops, crop_row=row, rain_pred=rain_pred, app=app, daily_kwh=daily,
             production_kg=row.predicted_yield_t_ha * p["farm_m2"] / 10, has_current=bool(len(cur)), kwp=kwp)
    a["score"] = score(p, bk, tank, row); a["recs"] = recommend(p, a); return a

def scenarios(M, plant, p, base):
    def mod(**kw): q = copy.deepcopy(p); q.update(kw); return q
    cut = mod(monthly_units=p["monthly_units"] * 0.8, appliances=[{**r, "Hours": (r["Hours"] or 0) * 0.8} for r in p["appliances"]])
    sc = [("Add 2 kWp of solar", mod(solar_kwp=p["solar_kwp"] + 2)), ("Add a 5 kWh battery", mod(battery_kwh=p.get("battery_kwh", 0.0) + 5)), ("Double the rainwater tank", mod(tank_l=p["tank_l"] * 2)),
          ("Cut electricity use by 20%", cut), ("Use only 100 L water/person/day", mod(lpcd=min(p["lpcd"], 100)))]
    if p["farm_m2"] > 0: sc.append(("Grow the best-suited crop", mod(current_crop="")))
    rows = [(n, analyze(M, plant, q)["score"]["total"]) for n, q in sc]
    return pd.DataFrame([(n, t, t - base) for n, t in rows], columns=["Action", "New score", "Gain"]).sort_values("Gain", ascending=False).reset_index(drop=True)

def recommend(p, a):
    recs = []; add = lambda mod, sev, msg: recs.append({"module": mod, "priority": sev, "recommendation": msg})
    o, k, app = a["outlook"], a["bk"], a["app"]; days = k["days"]
    if a["kwp"] <= 0:
        add("Energy", "High", f"You have no solar. About {a['daily_kwh'] / 4.5:.1f} kWp on your roof (roughly 4.5 kWh per kWp per day) could cover most of your {a['daily_kwh']:.1f} kWh/day use.")
    else:
        pk = o.solar_kw >= 0.8 * o.solar_kw.max()
        sh = app[(app.Shiftable) & (app.kWh_day > 0)]
        names = ", ".join(sh.Appliance.head(3)) or "heavy appliances"
        gain = min(sh.kWh_day.sum(), k["export_kwh"] / days) * 30 * p["tariff"]
        add("Energy", "High", f"Run {names} between {o.index[pk][0]:%H:%M} and {o.index[pk][-1]:%H:%M}, when predicted solar is at least 80% of its peak ({o.solar_kw.max():.1f} kW)"
            + (f" - worth up to ₹{gain:,.0f}/month." if gain >= 1 else "."))
        if k["self_sufficiency"] < 0.6:
            add("Energy", "Medium", f"Solar covers {k['self_sufficiency']:.0%} of your demand. A system of about {a['kwp'] * min(0.8 / max(k['self_sufficiency'], .1), 3):.1f} kWp could reach roughly 80%.")
        ev = (o.load_kw - o.solar_kw).clip(lower=0)[o.index.hour >= 18].sum() * 0.25
        if ev > 1 and p.get("battery_kwh", 0) < ev: add("Energy", "Medium", f"Evening shortfall tomorrow is about {ev:.1f} kWh; a battery of roughly {ev * 1.25:.0f} kWh would store midday surplus to cover it (see the score gain below).")
    if len(app) and app.kWh_day.sum() > 0 and p["energy_source"] == "Appliance list":
        t = app.sort_values("kWh_day", ascending=False).iloc[0]
        add("Energy", "Medium", f"Biggest consumer: {t.Appliance} ({t.kWh_day / app.kWh_day.sum():.0%} of your use). Check its efficiency rating or running hours.")
    pp = a["daily_kwh"] / p["persons"]
    if pp > 4: add("Energy", "Medium", f"You use {pp:.1f} kWh per person per day; efficient homes manage under about 3. Look at cooling and water-heating loads first.")
    t = a["tank"]; over = t.overflow_l.sum() / max(t.harvest_l.sum(), 1); rel = t.supplied_l.sum() / max(t.demand_l.sum(), 1)
    if p["roof_m2"] <= 0: add("Water", "Medium", "Add a roof catchment area to estimate how much rainwater you can harvest.")
    else:
        if over > 0.25: add("Water", "High", f"{over:.0%} of harvested rain overflows. Increase tank capacity above {p['tank_l']:,.0f} L to capture it.")
        if rel < 0.7: add("Water", "Medium", f"Harvested water meets only {rel:.0%} of your non-drinking/garden demand; add storage or cut garden and flush usage.")
    if p["lpcd"] > 135: add("Water", "Medium", f"You use {p['lpcd']:.0f} L/person/day, above the ~135 L benchmark. Fix leaks and fit aerators to save water.")
    top = a["monthly"].nlargest(3).index.tolist(); dry = a["monthly"].nsmallest(2).index.tolist()
    add("Water", "Low", f"Peak rainfall months are {', '.join(top)}: clean tanks before them. Budget stored water for {' and '.join(dry)}.")
    if p["farm_m2"] > 0 or p["garden_m2"] > 0:
        rp = a["rain_pred"]
        add("Agriculture", "High" if rp >= 5 else "Low", f"Predicted rainfall for the next day is {rp:.1f} mm: " + ("skip irrigation and let the tank fill." if rp >= 5 else "irrigate from stored rainwater if the soil is dry."))
    if p["farm_m2"] > 0:
        c = a["crops"]; b = c.iloc[0]
        if a["has_current"] and a["crop_row"].crop != b.crop:
            g = b.predicted_yield_t_ha / max(a["crop_row"].predicted_yield_t_ha, 1e-6) - 1
            add("Agriculture", "Medium", f"{a['crop_row'].crop} reaches {a['crop_row']['potential_%']:.0f}% of its potential here. {b.crop} is predicted to yield {g:+.0%} more per hectare.")
        else: add("Agriculture", "Medium", f"{b.crop} is the best fit for your conditions (~{b.predicted_yield_t_ha:.1f} t/ha, {b['potential_%']:.0f}% of potential). Runners-up: {', '.join(c.crop[1:3])}.")
        if p["soil_ph"] < 5.5 or p["soil_ph"] > 7.5: add("Agriculture", "Medium", f"Soil pH {p['soil_ph']:.1f} is outside the 5.5-7.5 range most crops prefer; consider lime (acidic) or organic matter (alkaline).")
    order = {"High": 0, "Medium": 1, "Low": 2}; return sorted(recs, key=lambda r: order[r["priority"]])

def report_html(p, a):
    sc = a["score"]; k = a["bk"]
    rows = "".join(f"<tr><td>{n}</td><td>{g}/{m}</td></tr>" for n, g, m in sc["items"])
    recs = "".join(f"<li><b>{r['module']} ({r['priority']})</b>: {r['recommendation']}</li>" for r in a["recs"])
    return f"""<html><head><meta charset="utf-8"><title>Sustainability report</title><style>body{{font-family:Segoe UI,Arial;max-width:800px;margin:30px auto;color:#1B2B21}}
h1{{color:#2E7D4F}}.s{{font-size:56px;font-weight:bold;color:#2E7D4F}}td,th{{border-bottom:1px solid #ccc;padding:6px 12px;text-align:left}}</style></head><body>
<h1>Eco Sphere - Sustainability Report</h1><p><b>{p['name']}</b> - {p['location']} - {p['persons']} people</p>
<div class="s">{sc['total']}/100 <small>Grade {sc['grade']}</small></div><table><tr><th>Component</th><th>Points</th></tr>{rows}</table>
<h3>Key figures</h3><ul><li>Daily electricity use: {a['daily_kwh']:.1f} kWh</li><li>Solar self-sufficiency: {k['self_sufficiency']:.0%}</li>
<li>Estimated monthly bill: Rs {k['bill_no_solar']:,.0f} without solar, Rs {k['bill_with_solar']:,.0f} with solar (saving Rs {k['saving_month']:,.0f})</li>
<li>CO2 avoided: {k['co2_saved_kg'] / k['days'] * 365:,.0f} kg/year</li></ul><h3>Recommendations</h3><ul>{recs}</ul>
<p><small>Solar data: Kaggle plant data. Energy, rainfall and crop models use simulated data; treat figures as estimates.</small></p></body></html>"""
