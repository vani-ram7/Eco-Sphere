"""Simple multiple-choice questionnaire -> numeric household profile."""
import profiles as pf
import places
from generate_datasets import CROPS

STEPS = ["Home", "Electricity", "Solar", "Water", "Farm"]
PEOPLE = ["1", "2", "3", "4", "5", "6", "7", "8+"]
APPS = [a["Appliance"] for a in pf.APPLIANCES]
HOME_SIZE = {"Small (1 BHK)": 0.6, "Medium (2-3 BHK)": 1.0, "Large (4 BHK or more)": 1.6}
USAGE = {"Low - I switch things off": 0.7, "Average": 1.0, "High - on most of the day": 1.4}
AC = {"2 hours/day": 2, "4 hours/day": 4, "6 hours/day": 6, "8 hours/day": 8, "10 hours/day": 10}
BILL = [500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 10000]
SOLAR = {"No solar yet": 0, "1 kW": 1, "2 kW": 2, "3 kW": 3, "5 kW": 5, "7 kW": 7, "10 kW": 10}
BATTERY = {"No battery": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}
ROOF = {"Small - 40 m²": 40, "Medium - 80 m²": 80, "Large - 150 m²": 150, "Very large - 250 m²": 250}
TANK = {"No tank": 0, "1,000 litres": 1000, "3,000 litres": 3000, "5,000 litres": 5000, "10,000 litres": 10000, "20,000 litres": 20000}
WATER = {"Careful - about 100 L per person/day": 100, "Average - about 135 L": 135, "High - about 180 L": 180}
RAINUSE = {"Toilet flushing only": 25, "Flushing + laundry": 40, "Flushing, laundry & cleaning": 50}
GARDEN = {"No garden": 0, "Small - 20 m²": 20, "Medium - 50 m²": 50, "Large - 150 m²": 150}
FARM = {"No farm or garden": 0, "Kitchen garden - 50 m²": 50, "Small plot - 200 m²": 200, "Medium plot - 1,000 m²": 1000, "Large - 1 acre (4,000 m²)": 4000}
NOCROP = "Not growing yet / undecided"
SOIL = {"Acidic (sour soil, pH ~5.5)": 5.5, "Neutral / not sure (pH ~6.5)": 6.5, "Alkaline (pH ~7.5)": 7.5}
FERT = {"Low (poor soil)": 50, "Medium": 100, "High (well manured)": 180}
SEASON = {"Dry year (~600 mm rain)": 600, "Normal season (~1,150 mm)": 1150, "Wet season (~1,800 mm)": 1800}

DEFAULT_ANS = dict(w_name="My Home", w_state="Kerala", w_dist="Thiruvananthapuram", w_place="", w_people="4",
                   w_apps=["LED lights", "Ceiling fans", "Refrigerator (effective hours)", "Television", "Washing machine", "Water pump", "Mixer / grinder", "Iron box", "Laptop / computer", "Wi-Fi router"],
                   w_size="Medium (2-3 BHK)", w_usage="Average", w_ac="6 hours/day", w_billmode=False, w_bill=1500,
                   w_solar="3 kW", w_battery="No battery", w_roof="Medium - 80 m²", w_tank="5,000 litres", w_wateruse="Average - about 135 L",
                   w_rainuse="Flushing, laundry & cleaning", w_garden="Medium - 50 m²", w_farm="Small plot - 200 m²", w_crop=NOCROP,
                   w_soil="Neutral / not sure (pH ~6.5)", w_fert="Medium", w_season="Normal season (~1,150 mm)", w_tariff=7.0, w_temp=26.0, w_hum=75, w_save=True)

def _label(a):
    place = (a.get("w_place") or "").strip(); d = a["w_dist"]
    return f"{(place or 'your area') if d == places.OTHER else d}, {a['w_state']}"

def build_profile(a):
    people = 8 if a["w_people"] == "8+" else int(a["w_people"]); size, use = HOME_SIZE[a["w_size"]], USAGE[a["w_usage"]]; rows = []
    for base in pf.APPLIANCES:
        n = base["Appliance"]
        if n not in a["w_apps"]: continue
        qty, hrs = base["Qty"] or 1, base["Hours"]
        if n in ("LED lights", "Ceiling fans"): qty = max(1, round(qty * size))
        if n not in ("Wi-Fi router", "Refrigerator (effective hours)"): hrs = hrs * use
        if n == "Air conditioner": hrs = AC[a["w_ac"]]
        rows.append({**base, "Qty": qty, "Hours": round(hrs, 2)})
    tariff = float(a["w_tariff"])
    return dict(name=(a["w_name"] or "").strip() or "My Home", location=_label(a), state=a["w_state"], district=a["w_dist"], place=(a.get("w_place") or "").strip(), persons=people, energy_source="Monthly bill" if a["w_billmode"] else "Appliance list",
                monthly_units=round(a["w_bill"] / max(tariff, 1), 1), tariff=tariff, appliances=rows, solar_kwp=float(SOLAR[a["w_solar"]]), battery_kwh=float(BATTERY[a["w_battery"]]),
                roof_m2=ROOF[a["w_roof"]], tank_l=TANK[a["w_tank"]], lpcd=WATER[a["w_wateruse"]], nonpotable=RAINUSE[a["w_rainuse"]], garden_m2=GARDEN[a["w_garden"]], irrig_l_m2=3.0,
                farm_m2=FARM[a["w_farm"]], temp_c=float(a["w_temp"]), season_rain=SEASON[a["w_season"]], humidity=int(a["w_hum"]), soil_ph=SOIL[a["w_soil"]], nitrogen=FERT[a["w_fert"]],
                current_crop="" if a["w_crop"] == NOCROP else a["w_crop"], wizard={k: (list(a[k]) if isinstance(a[k], (list, tuple)) else a[k]) for k in DEFAULT_ANS})

def _near(t, v): return min(t, key=lambda k: abs(t[k] - v))
def answers_from_profile(p):
    a = dict(DEFAULT_ANS)
    if p.get("wizard"):                                                      # saved by the questionnaire: restore exactly
        a.update({k: v for k, v in p["wizard"].items() if k in DEFAULT_ANS})
        if "w_state" not in p["wizard"]: a.update(_place_from_old(p))        # files saved before states/districts existed
        return a
    a.update(_place_from_old(p)); a.update(w_name=p["name"], w_people="8+" if p["persons"] >= 8 else str(int(p["persons"])), w_apps=[r["Appliance"] for r in p["appliances"] if r.get("Qty", 0) > 0 and r["Appliance"] in APPS],
             w_billmode=p["energy_source"] == "Monthly bill", w_tariff=float(p["tariff"]), w_solar=_near(SOLAR, p["solar_kwp"]), w_battery=_near(BATTERY, p.get("battery_kwh", 0)),
             w_roof=_near(ROOF, p["roof_m2"]), w_tank=_near(TANK, p["tank_l"]), w_wateruse=_near(WATER, p["lpcd"]), w_rainuse=_near(RAINUSE, p["nonpotable"]),
             w_garden=_near(GARDEN, p["garden_m2"]), w_farm=_near(FARM, p["farm_m2"]), w_soil=_near(SOIL, p["soil_ph"]), w_fert=_near(FERT, p["nitrogen"]),
             w_season=_near(SEASON, p["season_rain"]), w_temp=float(p["temp_c"]), w_hum=int(p["humidity"]), w_crop=p["current_crop"] or NOCROP)
    return a

def _place_from_old(p):
    first = (p.get("location") or "").split(",")[0].strip()
    return dict(w_state="Kerala", w_dist=first) if first in places.STATES["Kerala"] else {}
