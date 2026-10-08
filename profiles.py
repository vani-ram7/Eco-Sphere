"""Household profile storage (JSON files in /profiles) and defaults."""
import os, re, json, copy
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
APPLIANCES = [
    dict(Appliance="LED lights", Watts=10, Qty=8, Hours=6, Shiftable=False), dict(Appliance="Ceiling fans", Watts=60, Qty=3, Hours=10, Shiftable=False),
    dict(Appliance="Refrigerator (effective hours)", Watts=150, Qty=1, Hours=8, Shiftable=False), dict(Appliance="Television", Watts=100, Qty=1, Hours=4, Shiftable=False),
    dict(Appliance="Washing machine", Watts=500, Qty=1, Hours=0.7, Shiftable=True), dict(Appliance="Water pump", Watts=750, Qty=1, Hours=1, Shiftable=True),
    dict(Appliance="Mixer / grinder", Watts=300, Qty=1, Hours=0.3, Shiftable=False), dict(Appliance="Iron box", Watts=1000, Qty=1, Hours=0.3, Shiftable=True),
    dict(Appliance="Laptop / computer", Watts=80, Qty=1, Hours=5, Shiftable=False), dict(Appliance="Wi-Fi router", Watts=10, Qty=1, Hours=24, Shiftable=False),
    dict(Appliance="Air conditioner", Watts=1500, Qty=0, Hours=6, Shiftable=False), dict(Appliance="Water heater / geyser", Watts=2000, Qty=0, Hours=0.5, Shiftable=True),
    dict(Appliance="Induction stove", Watts=1800, Qty=0, Hours=1, Shiftable=False), dict(Appliance="EV charger", Watts=3300, Qty=0, Hours=2, Shiftable=True)]
DEFAULT = dict(name="My Home", location="Kerala, India", persons=4, energy_source="Appliance list", monthly_units=250.0, tariff=7.0, appliances=APPLIANCES,
               solar_kwp=3.0, battery_kwh=0.0, roof_m2=80, tank_l=5000, lpcd=135, nonpotable=50, garden_m2=50, irrig_l_m2=3.0,
               farm_m2=200, temp_c=26.0, season_rain=1150, humidity=75, soil_ph=6.2, nitrogen=100, current_crop="")
def _slug(n): return re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_") or "household"
def list_profiles():
    os.makedirs(DIR, exist_ok=True); out = []
    for f in sorted(os.listdir(DIR)):
        if f.endswith(".json"):
            try: out.append(json.load(open(os.path.join(DIR, f), encoding="utf-8"))["name"])
            except Exception: pass
    return out
def load_profile(name):
    p = copy.deepcopy(DEFAULT); p.update(json.load(open(os.path.join(DIR, _slug(name) + ".json"), encoding="utf-8"))); return p
def save_profile(p):
    os.makedirs(DIR, exist_ok=True); json.dump(p, open(os.path.join(DIR, _slug(p["name"]) + ".json"), "w", encoding="utf-8"), indent=2)
def delete_profile(name):
    f = os.path.join(DIR, _slug(name) + ".json")
    if os.path.exists(f): os.remove(f)
