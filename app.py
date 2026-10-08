import base64, glob, io, os
import plotly.io as pio
import numpy as np, pandas as pd, streamlit as st, plotly.express as px, plotly.graph_objects as go
import core, copy, json
import profiles as pf
import wizard as wz
import live, urllib.parse
from PIL import Image
from generate_datasets import CROPS

st.set_page_config(page_title="Eco Sphere - My Sustainability Score", page_icon="🌍", layout="wide")
st.markdown("<style>.kpi{padding:14px;border-radius:10px;color:white;text-align:center}.kpi h4{margin:0;font-size:15px}"
            ".kpi h3{margin:4px 0 0;font-size:26px}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------- background image (put pictures in the /assets folder)
@st.cache_data
def _bg_b64(path, mtime):
    """Open any image, shrink it to <=1600px and re-encode as JPEG so it always loads fast."""
    im = Image.open(path).convert("RGB"); im.thumbnail((1600, 1600))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()

# Dark-mode toggle (remembered in the page URL, so it survives a browser refresh)
if "dark" not in st.session_state:
    st.session_state["dark"] = st.query_params.get("mode") == "dark"
DARK = st.sidebar.toggle("🌙 Dark mode", key="dark")
st.query_params["mode"] = "dark" if DARK else "light"
def sty(fig):
    """Make every chart follow the dark/light theme with a transparent background."""
    fig.update_layout(template="plotly_dark" if DARK else "plotly", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#EAF2EC" if DARK else "#1B2B21"), legend=dict(font=dict(color="#EAF2EC" if DARK else "#1B2B21")))
    grid = "rgba(255,255,255,0.15)" if DARK else "rgba(0,0,0,0.10)"
    fig.update_xaxes(gridcolor=grid, tickfont=dict(color="#EAF2EC" if DARK else "#1B2B21")); fig.update_yaxes(gridcolor=grid, tickfont=dict(color="#EAF2EC" if DARK else "#1B2B21"))
    return fig

def set_background(shade=0.1):
    """shade: 0 = full picture, 1 = solid colour. Uses assets/background.* first, else any image in assets/."""
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    files = [f for e in ("jpg", "jpeg", "png", "webp") for f in glob.glob(os.path.join(folder, f"*.{e}"))]
    files.sort(key=lambda f: not os.path.basename(f).lower().startswith("background"))
    if not files:
        return
    b64 = _bg_b64(files[0], os.path.getmtime(files[0]))
    ov = "0,0,0" if DARK else "255,255,255"                 # overlay colour
    panel = "rgba(14,20,17,0.80)" if DARK else "rgba(255,255,255,0.80)"
    side = "rgba(14,20,17,0.90)" if DARK else "rgba(255,255,255,0.88)"
    txt = "#EAF2EC" if DARK else "#1B2B21"
    chart = "rgba(20,28,24,0.85)" if DARK else "rgba(255,255,255,0.92)"

    dark_css = """
    [data-testid="stAlert"] { background: rgba(40,70,60,0.55) !important; }
    [data-baseweb="input"], [data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-baseweb="base-input"] { background: #1c2822 !important; }
    input, [data-baseweb="select"] * { color: #EAF2EC !important; -webkit-text-fill-color: #EAF2EC !important; }
    [data-baseweb="popover"] > div, [data-baseweb="menu"], [data-baseweb="popover"] ul { background: #1c2822 !important; }
    [data-baseweb="menu"] *, [data-baseweb="popover"] li * { color: #EAF2EC !important; }
    [data-testid="stDownloadButton"] button, .stButton button[kind="secondary"] { background: #1c2822 !important; border-color: #3b5a4a !important; }
    [data-testid="stDownloadButton"] button *, .stButton button * { color: #EAF2EC !important; }
    [data-testid="stDataFrame"] { filter: invert(0.92) hue-rotate(180deg); }
    [data-testid="stTable"] table, [data-testid="stTable"] td, [data-testid="stTable"] th { background: transparent !important; color: #EAF2EC !important; border-color: #3b5a4a !important; }
    [data-testid="stSelectbox"] > div:last-child, [data-testid="stSelectbox"] > div:last-child div { background-color: #1c2822 !important; color: #EAF2EC !important; -webkit-text-fill-color: #EAF2EC !important; }
    [data-testid="stSelectbox"] svg { fill: #EAF2EC !important; }
    [data-testid="stSidebar"] > div:first-child { border-right: 1px solid #2f4a3c; }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"] { background: #1c2822 !important; color: #EAF2EC !important; -webkit-text-fill-color: #EAF2EC !important; }
    [data-testid="stExpander"] details, [data-testid="stVerticalBlockBorderWrapper"] { border-color: #3b5a4a !important; }
    [data-testid="stButtonGroup"] button[aria-pressed="false"] { background: #1c2822 !important; border: 1px solid #3b5a4a !important; }
    [data-testid="stButtonGroup"] button[aria-pressed="false"] * { color: #EAF2EC !important; }
    label:has(input[type=checkbox]:not(:checked)) > span:first-child { background: #3b5a4a !important; }
    .chip:not(.on) { color: #EAF2EC !important; }
    [data-testid="stBaseButton-secondary"] { background: #1c2822 !important; border-color: #3b5a4a !important; }
    [data-testid="stBaseButton-secondary"] * { color: #EAF2EC !important; }
    """ if DARK else ""
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba({ov},{shade}), rgba({ov},{shade})), url("data:image/jpeg;base64,{b64}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stSidebar"] > div:first-child {{ background: {side}; }}
    [data-testid="stMainBlockContainer"] {{ background: {panel}; border-radius: 18px; margin-top: 1.2rem; padding: 2rem 2.5rem 3rem; }}
    [data-testid="stPlotlyChart"] {{ background: {chart}; border-radius: 10px; }}
    h1, h2, h3, h4, label, p, [data-testid="stHeading"] *, [data-testid="stCaptionContainer"], [data-testid="stSidebar"] * {{ color: {txt} !important; }}
    .kpi, .kpi h3, .kpi h4 {{ color: #ffffff !important; }}
    {dark_css}
    </style>""", unsafe_allow_html=True)

set_background(shade=0.1)

def kpi(col, label, val, color): col.markdown(f'<div class="kpi" style="background:{color}"><h4>{label}</h4><h3>{val}</h3></div>', unsafe_allow_html=True)

@st.cache_resource(show_spinner="Training models on first launch…")
def models(): return core.train_all()
M = models()

# ---------------------------------------------------------------- sidebar: household selection
HERE = os.path.dirname(os.path.abspath(__file__))
ONLINE = os.environ.get("ECO_ONLINE") == "1" or HERE.startswith("/mount/src") or "SPACE_ID" in os.environ   # public web hosting: never store visitors' data
sb = st.sidebar
plant = sb.radio("Weather & solar data", [1, 2], format_func=lambda p: f"Plant {p}", horizontal=True, help="Which Kaggle solar plant supplies the weather/solar pattern")
DESKTOP = not ONLINE                                  # saved households only exist in the installed desktop app
saved = [] if ONLINE else pf.list_profiles(); sel = "➕ New household" if ONLINE else sb.selectbox("🏡 Household", ["➕ New household"] + saved)
if st.session_state.get("_sel") != sel:
    st.session_state["_sel"] = sel
    st.session_state["profile"] = pf.load_profile(sel) if sel in saved else wz.build_profile(wz.DEFAULT_ANS)
    st.session_state.update(wz.answers_from_profile(st.session_state["profile"])); st.session_state["step"] = 6 if sel in saved else 1
if not DESKTOP:
    up = sb.file_uploader("📂 Reload my saved answers (.json)", type="json")
    if up is not None and st.session_state.get("_up") != up.file_id:
        try:
            p_ = {**pf.DEFAULT, **json.loads(up.getvalue())}; st.session_state.update(wz.answers_from_profile(p_))
            st.session_state.update(profile=p_, _up=up.file_id, _own=True, step=6); st.rerun()
        except Exception: sb.error("That file couldn't be read.")
P = st.session_state["profile"]; A = core.analyze(M, plant, P); K = A["bk"]; SC = A["score"]
if not DESKTOP: sb.download_button("💾 Download my answers", json.dumps(P, indent=2), "my_eco_sphere.json", "application/json", help="Nothing is stored on the server. Keep this file to reload your answers next time.")
sb.caption("Solar: Kaggle plant data. Energy, rainfall & crop data are simulated (see README).")
if sel in saved and sb.button("🗑 Delete this household"):
    pf.delete_profile(sel); st.session_state["_sel"] = None; st.rerun()

st.title("🌍 Eco Sphere - My Sustainability Score")
if sel not in saved and not st.session_state.get("_own"):
    st.info("Showing a **sample household**. Answer the 5 short steps in the **🧾 My Household** tab to get your own score.")
tabs = st.tabs(["🧾 My Household", "📅 Today's Plan", "🏠 Overview", "☀️ Solar", "⚡ Energy", "💧 Water", "🌾 Farm & Crop", "🤖 Advisor"])

# ---------------------------------------------------------------- 1. guided questionnaire (dropdowns & tap-to-select chips)
st.markdown("""<style>
.hero{background:linear-gradient(120deg,#2E7D4F,#62b07c);padding:20px 26px;border-radius:16px;margin-bottom:14px}
.hero h2,.hero p{color:#fff !important;margin:0}.hero p{margin-top:4px;opacity:.95}
.stepper{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 14px}
.chip{padding:6px 15px;border-radius:20px;background:rgba(128,128,128,.2);font-size:14px}
.chip.on{background:#2E7D4F;font-weight:600}.chip.on,.chip.on *{color:#fff !important}.chip.done{background:rgba(46,125,79,.28)}
.result{display:flex;align-items:center;gap:26px;background:linear-gradient(120deg,#1f5f40,#2E7D4F);padding:22px 30px;border-radius:18px;margin-bottom:14px}
[data-testid="stButtonGroup"] button[aria-pressed="true"]{background:#2E7D4F !important;border-color:#2E7D4F !important}
[data-testid="stButtonGroup"] button[aria-pressed="true"] *{color:#fff !important}
[data-testid="stBaseButton-primary"]{background:#2E7D4F !important;border-color:#2E7D4F !important}[data-testid="stBaseButton-primary"] *{color:#fff !important}
.result *{color:#fff !important;margin:0}.result .big{font-size:76px;font-weight:800;line-height:1}
</style>""", unsafe_allow_html=True)
with tabs[0]:
    for k in wz.DEFAULT_ANS:                                  # keep answers alive while their step is not on screen
        if k in st.session_state: st.session_state[k] = st.session_state[k]
    step = st.session_state.get("step", 1)
    def goto(n): st.session_state["step"] = n
    def calc():
        newP = wz.build_profile(st.session_state)
        st.session_state["profile"] = newP; st.session_state["_own"] = True; st.session_state["step"] = 6
        if st.session_state.get("w_save", True) and not ONLINE: pf.save_profile(newP)
    st.markdown('<div class="hero"><h2>🌱 Let\'s find your Eco Score</h2><p>Just pick from the lists - 5 short steps, about 2 minutes.</p></div>', unsafe_allow_html=True)
    if step <= 5:
        chips = "".join(f'<span class="chip {"on" if i + 1 == step else "done" if i + 1 < step else ""}">{"✓" if i + 1 < step else i + 1}  {n}</span>' for i, n in enumerate(wz.STEPS))
        st.markdown(f'<div class="stepper">{chips}</div>', unsafe_allow_html=True)
    ss = st.session_state
    if step == 1:
        with st.container(border=True):
            st.markdown("### 🏡 About your home")
            c = st.columns(2); c[0].text_input("Name of your household", key="w_name"); c[1].selectbox("Where do you live?", wz.DISTRICTS, key="w_loc")
            st.radio("How many people live here?", wz.PEOPLE, horizontal=True, key="w_people")
    elif step == 2:
        with st.container(border=True):
            st.markdown("### ⚡ Electricity")
            st.pills("Tap everything you use at home", wz.APPS, selection_mode="multi", key="w_apps")
            c = st.columns(3); c[0].selectbox("Size of your home", list(wz.HOME_SIZE), key="w_size"); c[1].selectbox("How much do you use them?", list(wz.USAGE), key="w_usage")
            if "Air conditioner" in (ss.get("w_apps") or []): c[2].selectbox("Air conditioner runs", list(wz.AC), key="w_ac")
            st.toggle("I'd rather choose my monthly electricity bill", key="w_billmode")
            if ss.get("w_billmode"): st.select_slider("Typical monthly bill (₹)", wz.BILL, key="w_bill")
    elif step == 3:
        with st.container(border=True):
            st.markdown("### ☀️ Solar & battery")
            c = st.columns(2); c[0].selectbox("Rooftop solar size", list(wz.SOLAR), key="w_solar"); c[1].selectbox("Battery storage", list(wz.BATTERY), key="w_battery")
            st.caption("Not sure? A 3 kW system suits an average 2-3 bedroom home. Choose 'No solar yet' to see what solar could do for you.")
    elif step == 4:
        with st.container(border=True):
            st.markdown("### 💧 Water & rain")
            c = st.columns(2); c[0].selectbox("Roof area for collecting rain", list(wz.ROOF), key="w_roof"); c[1].selectbox("Rainwater tank", list(wz.TANK), key="w_tank")
            c = st.columns(2); c[0].selectbox("Your family's water use", list(wz.WATER), key="w_wateruse"); c[1].selectbox("Rainwater is used for", list(wz.RAINUSE), key="w_rainuse")
            st.selectbox("Garden you water", list(wz.GARDEN), key="w_garden")
    elif step == 5:
        with st.container(border=True):
            st.markdown("### 🌾 Farm or garden")
            st.selectbox("Do you grow food?", list(wz.FARM), key="w_farm")
            if wz.FARM[ss.get("w_farm", "No farm or garden")] > 0:
                c = st.columns(2); c[0].selectbox("Crop you grow now", [wz.NOCROP] + list(CROPS), key="w_crop"); c[1].selectbox("Soil type", list(wz.SOIL), key="w_soil")
                c = st.columns(2); c[0].selectbox("Soil richness", list(wz.FERT), key="w_fert"); c[1].selectbox("Rain this season", list(wz.SEASON), key="w_season")
            with st.expander("⚙️ Advanced (optional)"):
                c = st.columns(3); c[0].number_input("Electricity rate (₹/unit)", 1.0, 30.0, step=0.5, key="w_tariff"); c[1].number_input("Average temperature (°C)", 10.0, 45.0, step=0.5, key="w_temp")
                c[2].number_input("Humidity (%)", 20, 100, step=1, key="w_hum")
            if ONLINE: st.caption("🔒 Online version: your answers stay private to this browser tab and are not stored. Use 'Download my answers' in the sidebar to reuse them next time.")
            else: st.toggle("💾 Save this household so I can reopen it later", key="w_save")
    if step <= 5:
        n = st.columns([1, 3, 1.4])
        if step > 1: n[0].button("← Back", on_click=goto, args=(step - 1,), key=f"back{step}")
        if step < 5: n[2].button("Next →", type="primary", on_click=goto, args=(step + 1,), key=f"next{step}", width="stretch")
        else: n[2].button("✅ Calculate my score", type="primary", on_click=calc, key="calc", width="stretch")
    else:
        msg = {"A": "Excellent - you're a sustainability star!", "B": "Good - a few easy wins left", "C": "Fair - clear room to improve", "D": "Needs attention - big gains available"}[SC["grade"]]
        st.markdown(f'<div class="result"><div class="big">{SC["total"]}</div><div><h3>{P["name"]} - Grade {SC["grade"]}</h3><p>{msg}</p></div></div>', unsafe_allow_html=True)
        c = st.columns(3)
        kpi(c[0], "⚡ Solar covers", f"{K['self_sufficiency']:.0%}", "#1f77b4"); kpi(c[1], "💰 Saving / month", f"₹{K['saving_month']:,.0f}", "#2ca02c"); kpi(c[2], "🌱 CO₂ avoided / yr", f"{K['co2_saved_kg'] / K['days'] * 365:,.0f} kg", "#17a2b8")
        st.write(""); st.markdown("#### Your top 3 actions")
        for r in A["recs"][:3]: st.info(f"**{r['module']}** — {r['recommendation']}")
        st.success("👉 Open the **📅 Today's Plan** tab to see what to do today, based on the live weather forecast. The other tabs have the full picture.")
        st.button("✏️ Change my answers", on_click=goto, args=(1,), key="edit")

# ---------------------------------------------------------------- 1b. today's plan (live weather)
with tabs[1]:
    st.subheader("📅 What to do today - from the live weather forecast")
    lat, lon = live.LOCATIONS.get(P["location"], (None, None))
    if lat is None:
        c = st.columns(2); lat = c[0].number_input("Your latitude", -60.0, 60.0, 8.52, 0.01, key="lat"); lon = c[1].number_input("Your longitude", 60.0, 100.0, 76.94, 0.01, key="lon")
    @st.cache_data(ttl=1800, show_spinner=False)
    def _forecast(la, lo): return live.fetch_forecast(la, lo)
    with st.spinner("Getting the latest forecast…"): F = _forecast(round(lat, 2), round(lon, 2))
    if F is None:
        st.warning("Couldn't reach the weather service right now. Check your internet connection and press Refresh.")
    else:
        pl = live.make_plan(P, A, F, M["solar"][plant]); c = st.columns(3)
        kpi(c[0], "☀️ Solar today", f"{pl['days'][0]['solar_kwh']:.1f} kWh", "#ff7f0e"); kpi(c[1], "🌧 Rain tomorrow", f"{pl['days'][1]['rain']:.0f} mm", "#17a2b8"); kpi(c[2], "💰 Saving today", f"₹{pl['savings_today']:.0f}", "#2ca02c")
        st.write("")
        for ic, ti, tx in pl["cards"]:
            with st.container(border=True): st.markdown(f"#### {ic} {ti}"); st.markdown(tx)
        ch = pl["chart"]; f = go.Figure([go.Scatter(x=ch.index, y=ch.solar_kw, name="Your solar (kW)", fill="tozeroy", line_color="#ff7f0e"), go.Scatter(x=ch.index, y=ch.load_kw, name="Your demand (kW)", line_color="#1f77b4"),
                                          go.Bar(x=ch.index, y=ch.rain_mm, name="Rain (mm/h)", marker_color="rgba(23,162,184,0.6)", yaxis="y2")])
        f.update_layout(height=320, title="Next 48 hours", yaxis_title="kW", yaxis2=dict(overlaying="y", side="right", title="mm", showgrid=False)); st.plotly_chart(sty(f), width="stretch", theme=None)
        d = st.columns([1, 1, 3]); d[0].link_button("📲 Share on WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(pl["share"])); d[1].button("🔄 Refresh", on_click=_forecast.clear)
        with st.expander("Message you can copy"): st.code(pl["share"], language=None)
        st.caption(f"Forecast: Open-Meteo, for {P['location']}, local time {F['now']:%d %b %H:%M}. Solar output uses the trained model on forecast sunshine and temperature. Estimates only.")

# ---------------------------------------------------------------- 2. overview
with tabs[2]:
    a, b = st.columns([1, 2])
    fig = go.Figure(go.Indicator(mode="gauge+number", value=SC["total"], title={"text": f"{P['name']} - Grade {SC['grade']}"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#2ca02c"}, "steps": [{"range": [0, 50], "color": "#f8d7da"}, {"range": [50, 80], "color": "#fff3cd"}, {"range": [80, 100], "color": "#d4edda"}]}))
    fig.update_layout(height=270, margin=dict(t=60, b=0)); a.plotly_chart(sty(fig), width="stretch", theme=None)
    it = pd.DataFrame(SC["items"], columns=["Component", "Points", "Max"]); it["Missing"] = it.Max - it.Points
    f = go.Figure([go.Bar(y=it.Component, x=it.Points, orientation="h", name="Earned", marker_color="#2ca02c"), go.Bar(y=it.Component, x=it.Missing, orientation="h", name="Room to improve", marker_color="rgba(150,150,150,0.45)")])
    f.update_layout(barmode="stack", height=250, margin=dict(t=30, b=0), yaxis=dict(autorange="reversed"), title="Where your points come from"); b.plotly_chart(sty(f), width="stretch", theme=None)
    c = st.columns(4)
    kpi(c[0], "⚡ Solar self-sufficiency", f"{K['self_sufficiency']:.0%}", "#1f77b4"); kpi(c[1], "💰 Bill saving / month", f"₹{K['saving_month']:,.0f}", "#2ca02c")
    kpi(c[2], "🌱 CO₂ avoided / year", f"{K['co2_saved_kg'] / K['days'] * 365:,.0f} kg", "#17a2b8"); kpi(c[3], "💧 Water demand met", f"{A['tank'].supplied_l.sum() / max(A['tank'].demand_l.sum(), 1):.0%}", "#6f42c1")
    st.write("")
    st.subheader("Top recommendations")
    for r in A["recs"][:4]: st.info(f"**{r['module']} · {r['priority']}** — {r['recommendation']}")
    o = A["outlook"]; st.subheader("Next-day energy outlook (predicted)")
    f = go.Figure([go.Scatter(x=o.index, y=o.solar_kw, name="Your solar (kW)", fill="tozeroy", line_color="#ff7f0e"), go.Scatter(x=o.index, y=o.load_kw, name="Your demand (kW)", line_color="#1f77b4")])
    f.update_layout(height=300, yaxis_title="kW"); st.plotly_chart(sty(f), width="stretch", theme=None)

# ---------------------------------------------------------------- 3. solar
S = M["solar"][plant]
with tabs[3]:
    d = S["data"]; c = st.columns(4)
    kpi(c[0], "⚡ Avg Power", f"{d.AC_POWER.mean():.2f}", "#1f77b4"); kpi(c[1], "🔆 Max Power", f"{d.AC_POWER.max():.2f}", "#ff7f0e")
    kpi(c[2], "🌡 Avg Temp", f"{d.AMBIENT_TEMPERATURE.mean():.2f}", "#2ca02c"); kpi(c[3], "☀ Avg Irradiation", f"{d.IRRADIATION.mean():.2f}", "#d62728")
    m = S["metrics"]; st.caption(f"Random Forest on hold-out (last 20% of days): R² {m['R2']:.3f} · MAE {m['MAE']:.1f} kW · RMSE {m['RMSE']:.1f} kW")
    st.success(f"Your {P['solar_kwp']:.1f} kWp system is estimated to generate **{K['solar_kwh'] / K['days']:.1f} kWh per day** on average." if P["solar_kwp"] > 0 else "You have no solar yet - enter a system size in My Household to see its output.")
    t = S["test"]; f = go.Figure([go.Scatter(x=t.DATE_TIME, y=t.AC_POWER, name="Actual"), go.Scatter(x=t.DATE_TIME, y=t.PREDICTED, name="Predicted")])
    f.update_layout(height=320, yaxis_title="AC power (kW / inverter)", title="Predicted vs actual (hold-out period)"); st.plotly_chart(sty(f), width="stretch", theme=None)
    l, r = st.columns(2)
    l.plotly_chart(sty(px.scatter(d.sample(min(2500, len(d)), random_state=1), x="IRRADIATION", y="AC_POWER", color="MODULE_TEMPERATURE", title="Irradiation vs power")), width="stretch", theme=None)
    r.plotly_chart(sty(px.bar(x=list(S["importance"]), y=list(S["importance"].values()), labels={"x": "", "y": "importance"}, title="Feature importance")), width="stretch", theme=None)
    st.subheader("🤖 Predict solar power")
    p = st.columns(3); at = p[0].number_input("Ambient temperature (°C)", value=26.0); mt = p[1].number_input("Module temperature (°C)", value=40.0); ir = p[2].number_input("Irradiation (kW/m²)", 0.0, 1.5, 0.6, 0.05)
    st.success(f"Predicted AC power: **{S['model'].predict(pd.DataFrame([[at, mt, ir]], columns=core.SOLAR_FEATS))[0]:.1f} kW** per inverter")

# ---------------------------------------------------------------- 4. energy
with tabs[4]:
    bal = A["bal"]; c = st.columns(4)
    kpi(c[0], "🏠 Daily use", f"{A['daily_kwh']:.1f} kWh", "#1f77b4"); kpi(c[1], "☀ Solar / day", f"{K['solar_kwh'] / K['days']:.1f} kWh", "#ff7f0e")
    kpi(c[2], "🧾 Bill / month", f"₹{K['bill_with_solar']:,.0f}", "#2ca02c"); kpi(c[3], "📉 Without solar", f"₹{K['bill_no_solar']:,.0f}", "#d62728")
    st.caption(f"Your demand follows the ML household-load pattern (R² {M['energy']['metrics']['R2']:.2f}) scaled to your own {A['daily_kwh']:.1f} kWh/day. Surplus exported: {K['export_kwh'] / K['days']:.1f} kWh/day.")
    hourly = bal.groupby(bal.index.hour).mean(); f = go.Figure([go.Scatter(x=hourly.index, y=hourly.solar_kw, name="Avg solar", fill="tozeroy", line_color="#ff7f0e"), go.Scatter(x=hourly.index, y=hourly.load_kw, name="Avg demand", line_color="#1f77b4")])
    f.update_layout(height=320, xaxis_title="Hour of day", yaxis_title="kW", title="Your average daily profile"); st.plotly_chart(sty(f), width="stretch", theme=None)
    l, r = st.columns(2)
    ap = A["app"].query("kWh_day > 0").sort_values("kWh_day"); r.plotly_chart(sty(px.bar(ap, x="kWh_day", y="Appliance", orientation="h", title="Where your electricity goes (kWh/day)", color_discrete_sequence=["#2ca02c"])), width="stretch", theme=None)
    daily = bal.resample("D").sum() * 0.25; l.plotly_chart(sty(px.bar(daily, y=["solar_kw", "load_kw"], barmode="group", labels={"value": "kWh", "DATE_TIME": ""}, title="Daily solar vs your demand (kWh)")), width="stretch", theme=None)
    t = M["energy"]["test"]; f = go.Figure([go.Scatter(x=t.index, y=t.ACTUAL, name="Actual"), go.Scatter(x=t.index, y=t.PREDICTED, name="Predicted")]); f.update_layout(height=300, title="Load-forecast model check (hold-out, typical home)", yaxis_title="kW")
    st.plotly_chart(sty(f), width="stretch", theme=None)

# ---------------------------------------------------------------- 5. water
with tabs[5]:
    rf = A["tank"]; mo = A["monthly"]; c = st.columns(4)
    kpi(c[0], "🌧 Harvested (2024)", f"{rf.harvest_l.sum() / 1000:,.0f} kL", "#17a2b8"); kpi(c[1], "🚿 Supplied", f"{rf.supplied_l.sum() / 1000:,.0f} kL", "#2ca02c")
    kpi(c[2], "🌊 Overflow lost", f"{rf.overflow_l.sum() / 1000:,.0f} kL", "#d62728"); kpi(c[3], "📅 Tomorrow's rain", f"{A['rain_pred']:.1f} mm", "#6f42c1")
    R = M["rain"]; st.caption(f"Daily demand met from rain: {rf.demand_l.iloc[0]:,.0f} L (household + garden). Next-day rain model R² {R['metrics']['R2']:.2f}: treat as a guide; monthly patterns are the reliable planning signal.")
    l, r = st.columns(2)
    l.plotly_chart(sty(px.bar(x=mo.index, y=mo.values, labels={"x": "", "y": "mm"}, title="Average monthly rainfall (2015-2024)")), width="stretch", theme=None)
    pot = mo * P["roof_m2"] * 0.8; r.plotly_chart(sty(px.bar(x=pot.index, y=pot.values / 1000, labels={"x": "", "y": "kL"}, title=f"Harvest potential ({P['roof_m2']} m² roof)", color_discrete_sequence=["#17a2b8"])), width="stretch", theme=None)
    f = go.Figure([go.Scatter(x=rf.index, y=rf.storage_l, name="Tank level (L)", fill="tozeroy"), go.Bar(x=rf.index, y=rf.overflow_l, name="Overflow (L)", marker_color="#d62728")])
    f.update_layout(height=320, title=f"2024 tank simulation ({P['tank_l']:,} L tank, {P['persons']} people)"); st.plotly_chart(sty(f), width="stretch", theme=None)

# ---------------------------------------------------------------- 6. crop
with tabs[6]:
    Cm = M["crop"]; cr = A["crops"]; row = A["crop_row"]; m = Cm["metrics"]
    if P["farm_m2"] <= 0: st.info("You entered no farm area, so the Crop component is excluded from your score. Add a farm or kitchen-garden area in My Household to include it.")
    st.caption(f"Crop-yield model (Random Forest) hold-out: R² {m['R2']:.3f} · MAE {m['MAE']:.2f} t/ha")
    l, r = st.columns([3, 2])
    l.plotly_chart(sty(px.bar(cr, x="crop", y="predicted_yield_t_ha", color="potential_%", color_continuous_scale="Greens", title="Predicted yield for your conditions (t/ha)")), width="stretch", theme=None)
    r.dataframe(cr.round(2), width="stretch", hide_index=True)
    st.success(f"🌱 Best fit: **{cr.crop[0]}** (~{cr.predicted_yield_t_ha[0]:.1f} t/ha, {cr['potential_%'][0]:.0f}% of potential)")
    if P["farm_m2"] > 0: st.info(f"Estimated production of **{row.crop}** on {P['farm_m2']:,} m²: **~{A['production_kg']:,.0f} kg** per season" + ("" if A["has_current"] else " (best-fit crop; pick your crop in My Household to compare)."))
    sel_c = st.selectbox("Rainfall sensitivity for", list(CROPS)); xs = np.arange(200, 2201, 100)
    ys = [core.rank_crops(Cm, x, P["temp_c"], P["humidity"], P["soil_ph"], P["nitrogen"]).set_index("crop").loc[sel_c, "predicted_yield_t_ha"] for x in xs]
    st.plotly_chart(sty(px.line(x=xs, y=ys, labels={"x": "Season rainfall (mm)", "y": "t/ha"}, title=f"{sel_c}: yield vs rainfall (what-if)")), width="stretch", theme=None)

# ---------------------------------------------------------------- 7. advisor
with tabs[7]:
    st.subheader("Recommendations for " + P["name"]); icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
    for r in A["recs"]: st.markdown(f"{icon[r['priority']]} **{r['module']}** ({r['priority']}) — {r['recommendation']}")
    st.subheader("📈 How could you raise your score?")
    sc = core.scenarios(M, plant, P, SC["total"]); st.dataframe(sc, hide_index=True, width="stretch")
    st.plotly_chart(sty(px.bar(sc, x="Gain", y="Action", orientation="h", title=f"Score gain vs today ({SC['total']})", color_discrete_sequence=["#2ca02c"])), width="stretch", theme=None)
    st.subheader("☀️ Is solar worth it for you?")
    c = st.columns(2); cost_kw = c[0].number_input("Installed cost (₹ per kW)", 30000, 150000, 62000, 1000); use_sub = c[1].toggle("Include PM Surya Ghar central subsidy", True)
    rows = []
    for k in [1, 2, 3, 4, 5, 7, 10]:
        q = copy.deepcopy(P); q.update(solar_kwp=float(k), battery_kwh=0.0); yr = core.analyze(M, plant, q)["bk"]["saving_month"] * 12
        net = cost_kw * k - ((30000 * min(k, 2) + (18000 if k >= 3 else 0)) if use_sub else 0)
        rows.append({"System (kW)": k, "Net cost (₹)": round(net), "Saving per year (₹)": round(yr), "Payback (years)": round(net / yr, 1) if yr > 0 else None, "25-year gain (₹)": round(yr * 25 - net)})
    roi = pd.DataFrame(rows); st.dataframe(roi, hide_index=True, width="stretch"); ok = roi.dropna(subset=["Payback (years)"])
    if len(ok): b = ok.loc[ok["Payback (years)"].idxmin()]; st.success(f"Fastest payback for your home: **{int(b['System (kW)'])} kW**, about **{b['Payback (years)']} years**. Beyond what your home can use, extra panels only export power and pay back more slowly.")
    st.caption("Central subsidy: ₹30,000/kW for the first 2 kW plus ₹18,000 for the 3rd kW, capped at ₹78,000 (PM Surya Ghar: Muft Bijli Yojana). Rules, state top-ups and prices change - confirm at pmsuryaghar.gov.in and get installer quotes. Savings count only the electricity you use yourself; if your utility credits exported power (net metering), real savings are higher. Ignores panel ageing and tariff changes.")
    st.subheader("⬇️ Downloads"); d = st.columns(3)
    d[0].download_button("Sustainability report (HTML)", core.report_html(P, A), f"{P['name']}_report.html", "text/html")
    d[1].download_button("Recommendations (CSV)", pd.DataFrame(A["recs"]).to_csv(index=False), "recommendations.csv", "text/csv")
    d[2].download_button("Household profile (JSON)", json.dumps(P, indent=2), f"{P['name']}_profile.json", "application/json")
    st.subheader("SDG alignment"); st.table(pd.DataFrame({"SDG": ["7 Affordable & Clean Energy", "6 Clean Water", "11 Sustainable Cities", "13 Climate Action", "2 Zero Hunger"],
        "Your contribution": [f"Solar covers {K['self_sufficiency']:.0%} of demand", f"{A['tank'].supplied_l.sum() / 1000:,.0f} kL/yr supplied by rain", "Integrated home resource planning",
                              f"{K['co2_saved_kg'] / K['days'] * 365:,.0f} kg CO₂ avoided/yr", "Crop choice guided by predicted yield"]}))
