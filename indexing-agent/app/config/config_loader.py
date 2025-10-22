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
        config_data = yaml.safe_load(file)

    # ✅ Get current working directory
    current_dir = os.getcwd()

    # ✅ Create output_dir and input_dir under current directory
    output_dir_path = os.path.join(current_dir, "output_dir")
    input_dir_path = os.path.join(current_dir, "input_dir")

    os.makedirs(output_dir_path, exist_ok=True)
    os.makedirs(input_dir_path, exist_ok=True)

    # ✅ Update config paths
    if "files" not in config_data:
        config_data["files"] = {}

    config_data["files"]["output_directory"] = output_dir_path
    config_data["files"]["data_directory"] = input_dir_path
    return config_data

# ✅ Load config once, globally accessible
config = load_config()
