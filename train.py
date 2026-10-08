"""Train all models, print evaluation metrics and save them to /models."""
import os, joblib
from core import train_all
M = train_all(); os.makedirs("models", exist_ok=True)
for name, obj in [("solar_plant1", M["solar"][1]), ("solar_plant2", M["solar"][2]), ("energy", M["energy"]), ("rainfall", M["rain"]), ("crop", M["crop"])]:
    joblib.dump(obj["model"], f"models/{name}_model.pkl")
    print(f"{name:13s}", {k: round(v, 3) for k, v in obj["metrics"].items()})
