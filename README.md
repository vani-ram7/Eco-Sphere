# Eco Sphere - AI Sustain-o-meter (web version)

A free web app that turns a household's answers + the **live weather forecast** into things to do *today*:
when to run the washing machine/pump on solar, how much rain your roof will collect, when to skip irrigation, heat and heavy-rain alerts,
whether rooftop solar (with the PM Surya Ghar subsidy) is worth it, plus a sustainability score. Share the daily plan on WhatsApp.

## Run on your PC
```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

## Put it online (free link anyone can open)
See **DEPLOY.md** - step by step, about 10 minutes.

## Privacy
When hosted online the app stores nothing on the server. Answers live only in the visitor's browser tab; they can download a small JSON file and reload it next time.
Only the district's approximate coordinates are sent to the weather service (Open-Meteo).

## Files
`app.py` interface · `live.py` live weather → daily plan · `core.py` models, scoring, recommendations · `wizard.py` questionnaire · `profiles.py` · `data/` · `assets/`

## Honest notes
* Solar data is real Kaggle plant data; energy, rainfall and crop datasets are simulated (replace the CSVs in `data/` with real data, same columns).
* Solar forecast = trained model applied to forecast sunshine and temperature, scaled to the user's kWp. Estimates only.
* Subsidy and prices change; always confirm at pmsuryaghar.gov.in and with installers.
