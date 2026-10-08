"""Live weather (Open-Meteo, free, no API key) -> today's practical action plan."""
import os, json, urllib.request, urllib.parse
import numpy as np, pandas as pd
import core

LOCATIONS = {"Thiruvananthapuram": (8.52, 76.94), "Kollam": (8.89, 76.61), "Pathanamthitta": (9.26, 76.79), "Alappuzha": (9.50, 76.34), "Kottayam": (9.59, 76.52),
             "Idukki": (9.85, 76.97), "Ernakulam": (9.98, 76.30), "Thrissur": (10.53, 76.21), "Palakkad": (10.79, 76.65), "Malappuram": (11.05, 76.07),
             "Kozhikode": (11.26, 75.78), "Wayanad": (11.69, 76.13), "Kannur": (11.87, 75.37), "Kasaragod": (12.50, 74.99), "Coimbatore": (11.02, 76.96)}

def _mock():
    """Offline demo/test data in the Open-Meteo shape: sunny today, rainy tomorrow, mixed day after."""
    idx = pd.date_range(pd.Timestamp.now().normalize(), periods=72, freq="h"); h = idx.hour.values; day = np.arange(72) // 24
    sun = np.clip(np.sin((h - 6) / 12 * np.pi), 0, None); cloud = np.array([0.15, 0.85, 0.35])[day]
    rain = np.where((day == 1) & (h >= 14) & (h <= 19), 9.0, 0.0); tm = 26 + 8 * sun + np.where(day == 2, 2, 0)
    hourly = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in idx], "temperature_2m": tm.round(1).tolist(), "precipitation": rain.tolist(),
              "precipitation_probability": np.where(rain > 0, 85, 10).tolist(), "shortwave_radiation": (950 * sun * (1 - 0.75 * cloud)).round().tolist(), "cloud_cover": (cloud * 100).tolist()}
    days = sorted({t[:10] for t in hourly["time"]}); df = pd.DataFrame(hourly); df["d"] = df.time.str[:10]
    daily = {"time": days, "precipitation_sum": df.groupby("d").precipitation.sum().tolist(), "temperature_2m_max": df.groupby("d").temperature_2m.max().tolist(),
             "precipitation_probability_max": df.groupby("d").precipitation_probability.max().tolist()}
    return {"hourly": hourly, "daily": daily, "utc_offset_seconds": 19800, "_mock_now": pd.Timestamp.now()}

def fetch_forecast(lat, lon):
    """Returns {'hourly','daily','now'} or None if the service can't be reached."""
    if os.environ.get("ECO_MOCK_WEATHER") == "1": raw = _mock()
    else:
        q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 3,
                                    "hourly": "temperature_2m,precipitation,precipitation_probability,shortwave_radiation,cloud_cover",
                                    "daily": "precipitation_sum,temperature_2m_max,precipitation_probability_max"})
        try: raw = json.load(urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?" + q, timeout=8))
        except Exception: return None
    try:
        h = pd.DataFrame(raw["hourly"]); h["time"] = pd.to_datetime(h["time"]); d = pd.DataFrame(raw["daily"]); d["time"] = pd.to_datetime(d["time"])
        now = raw.get("_mock_now") or (pd.Timestamp.now("UTC").tz_localize(None) + pd.Timedelta(seconds=raw.get("utc_offset_seconds", 19800)))
        return {"hourly": h.set_index("time").fillna(0), "daily": d.set_index("time").fillna(0), "now": now}
    except Exception: return None

def solar_series(hourly, S, kwp):
    """Forecast radiation + temperature -> our trained solar model -> kW from the user's own array."""
    irr = (hourly["shortwave_radiation"] / 1000).clip(0, 1.3).values; amb = hourly["temperature_2m"].values
    X = pd.DataFrame({"AMBIENT_TEMPERATURE": amb, "MODULE_TEMPERATURE": amb + 32 * irr, "IRRADIATION": irr})[core.SOLAR_FEATS]
    return pd.Series(core.to_home_kw(S["model"].predict(X), S["data"]["AC_POWER"], kwp), index=hourly.index)

def make_plan(P, A, F, S):
    sol = solar_series(F["hourly"], S, P["solar_kwp"]); lb = A["bal"].groupby(A["bal"].index.hour)["load_kw"].mean()
    load = pd.Series([lb.get(x, lb.mean()) for x in sol.index.hour], index=sol.index)
    sh = A["app"][(A["app"].Shiftable) & (A["app"].kWh_day > 0)]; shift_kwh = float(sh.kWh_day.sum()) or 1.5
    names = ", ".join(sh.Appliance.head(3)) or "your washing machine and water pump"; typical = max(A["bk"]["solar_kwh"] / A["bk"]["days"], 0.1)
    now, tariff, days = F["now"], P["tariff"], []
    for i, d in enumerate(F["daily"].index[:2]):
        m = sol.index.normalize() == d; s, l = sol[m], load[m]; el = s[s.index >= now.floor("h")] if i == 0 else s
        win, surplus = None, 0.0
        if len(el) and el.max() >= 0.3:
            ok = el >= 0.7 * el.max(); idx = el.index[ok]; win = (idx[0], idx[-1] + pd.Timedelta(hours=1)); surplus = float((el - l.reindex(el.index)).clip(lower=0).sum())
        days.append(dict(date=d, solar_kwh=float(s.sum()), used_kwh=float(np.minimum(s, l).sum()), load_kwh=float(l.sum()), win=win, savings=min(shift_kwh, surplus) * tariff,
                         rain=float(F["daily"]["precipitation_sum"].iloc[i]), prob=float(F["daily"]["precipitation_probability_max"].iloc[i]), tmax=float(F["daily"]["temperature_2m_max"].iloc[i])))
    t, tm = days[0], days[1]; cards = []; fmt = lambda x: f"{x:%H:%M}"
    if P["solar_kwp"] > 0:
        r = t["solar_kwh"] / typical; tag = "Sunny day ☀️" if r >= 0.9 else "Partly cloudy ⛅" if r >= 0.6 else "Cloudy - low solar ☁️"
        cards.append(("☀️", f"Solar today: {tag}", f"Your {P['solar_kwp']:g} kW system should make about {t['solar_kwh']:.1f} kWh ({r:.0%} of its usual output). "
                      f"Your home can use about {t['used_kwh']:.1f} kWh of it directly (~{t['used_kwh'] / max(t['load_kwh'], .1):.0%} of today's demand)."
                      + (" Postpone heavy appliances to a sunnier day if you can." if r < 0.6 else "")))
        for lab, dd in (("today", t), ("tomorrow", tm)):
            if dd["win"]:
                cards.append(("⏰", f"Best time to run appliances {lab}", f"Run **{names}** between **{fmt(dd['win'][0])} and {fmt(dd['win'][1])}** - solar will cover them" + (f", saving about **₹{dd['savings']:.0f}**." if dd["savings"] >= 1 else "."))); break
    else: cards.append(("☀️", "Solar could help you", f"Today's forecast gives about {t['solar_kwh'] / max(P['solar_kwp'], 1):.1f} kWh per kW (for a 1 kW system, use the 'Is solar worth it' calculator in the Advisor tab)."))
    wet = max(days, key=lambda x: x["rain"]); lab = "today" if wet is t else "tomorrow"; harvest = P["roof_m2"] * wet["rain"] * 0.8
    if wet["rain"] >= 60: cards.append(("⛈️", f"Very heavy rain expected {lab} ({wet['rain']:.0f} mm)", "Clear gutters and drains now and check that your tank overflow pipe works. Avoid using electrical appliances near wet areas and keep phones charged."))
    elif wet["rain"] >= 5:
        cards.append(("🌧️", f"Rain expected {lab}: {wet['rain']:.0f} mm ({wet['prob']:.0f}% chance)", f"Your roof can collect about **{harvest:,.0f} litres**."
                      + (f" That is more than your {P['tank_l']:,} L tank holds - use stored water first to make space." if P["tank_l"] and harvest > P["tank_l"] * 0.8 else "")
                      + (" Skip irrigation and let the rain do the work." if P["garden_m2"] or P["farm_m2"] else "")))
    else: cards.append(("🌤️", "No significant rain in the next 2 days", "Use stored rainwater first and water plants early in the morning or evening to cut evaporation." if P["tank_l"] else "Water plants early in the morning or evening to cut evaporation."))
    hot = max(days, key=lambda x: x["tmax"])
    if hot["tmax"] >= 34: cards.append(("🌡️", f"Hot day ahead ({hot['tmax']:.0f}°C)", "Set the AC to 26 °C or use fans (rule of thumb: each degree higher saves roughly 6% cooling energy), close curtains by noon, and drink plenty of water."))
    if P["farm_m2"] > 0 and wet["rain"] < 5 and hot["tmax"] >= 32: cards.append(("🌾", "Protect your crops", "Irrigate between 5 and 8 am, mulch the soil to hold moisture, and avoid fertiliser on very hot days."))
    sd = A["app"]; txt = f"🌍 Eco Sphere plan for {P['name']} ({t['date']:%d %b})\n" + "\n".join(f"{ic} {ti}: {tx}".replace("**", "") for ic, ti, tx in cards) + "\n\nTry it: Eco Sphere - AI Sustain-o-meter"
    chart = pd.DataFrame({"solar_kw": sol, "load_kw": load, "rain_mm": F["hourly"]["precipitation"]}).loc[lambda x: x.index.normalize() <= F["daily"].index[1]]
    return dict(days=days, cards=cards, chart=chart, share=txt, savings_today=t["savings"] if t["win"] else tm["savings"])
