# app/config/config_loader.py
import os
import yaml

def load_config(filename="config.yaml"):
    # ✅ Get the absolute path to config.yaml inside the config folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")

    with open(path, "r") as file:
        return yaml.safe_load(file)

# ✅ Load config once, globally accessible
config = load_config()
