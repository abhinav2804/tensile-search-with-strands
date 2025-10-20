# utils/file_utils.py
import os
import json
import csv
import logging
from app.config.config_loader import config

logger = logging.getLogger(__name__)

def read_file_in_chunks(file_path, chunk_size=None):
    """Read any file in fixed-size character chunks, skipping blank lines."""
    if chunk_size is None:
        chunk_size = config["app"]["chunk_size"]

    buffer = ""
    with open(file_path, 'r', encoding="utf-8") as file:
        while True:
            data = file.read(chunk_size)
            if not data:
                break

            buffer += data
            lines = buffer.split("\n")
            buffer = lines.pop()  # keep partial line

            for line in lines:
                if line.strip():  # skip empty lines
                    yield line

        if buffer.strip():  # last line check
            yield buffer

def read_file_by_lines(file_path):
    """Read file line-by-line (for JSONL, CSV, text docs)."""
    with open(file_path, 'r', encoding="utf-8") as file:
        for line in file:
            yield line.strip()

def detect_file_type(file_path):
    """Detect file type based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".json"]:
        return "json"
    elif ext in [".jsonl"]:
        return "jsonl"
    elif ext in [".csv"]:
        return "csv"
    elif ext in [".txt"]:
        return "text"
    else:
        return "unknown"

def read_structured_file(file_path):
    """Read structured file into logical chunks (records)."""
    file_type = detect_file_type(file_path)

    if file_type == "json":
        with open(file_path, 'r', encoding="utf-8") as file:
            data = json.load(file)
            for item in data:
                yield item

    elif file_type == "jsonl":
        with open(file_path, 'r', encoding="utf-8") as file:
            for line in file:
                yield json.loads(line)

    elif file_type == "csv":
        with open(file_path, 'r', encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                yield row

    elif file_type == "text":
        yield from read_file_by_lines(file_path)

    else:
        # 🚨 Unknown file type — fallback to raw text chunks
        logger.warning(f"Unknown file type for '{file_path}'. Falling back to raw text read.")
        yield from read_file_in_chunks(file_path, config["app"]["chunk_size"])

def write_data_to_file(file_path, data):
    """Overwrite file with given data."""
    with open(file_path, 'w', encoding="utf-8") as file:
        file.write(data)

def append_data_to_file(file_path, data):
    """Append given data to file."""
    with open(file_path, 'a', encoding="utf-8") as file:
        file.write(data)

def reset_output_files(config, user_id):
    """
    Safely clears schema.json, readme.txt, and data.json in the user's output directory.
    If the directory doesn't exist, it will be created.
    Creates empty placeholders so downstream code won't break.
    """
    # Ensure trailing slash handling + safe join
    output_dir = os.path.join(config["files"]["output_directory"], str(user_id))

    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"📂 Output directory ready: {output_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to create output directory: {e}")
        raise

    schema_path = os.path.join(output_dir, "schema.json")
    readme_path = os.path.join(output_dir, "readme.txt")
    data_json_path = os.path.join(output_dir, "data.json")

    try:
        # --- Empty schema.json ---
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        logger.info(f"✅ Cleared schema file: {schema_path}")

        # --- Empty readme.txt ---
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("No readme provided")
        logger.info(f"✅ Cleared readme file: {readme_path}")

        # --- Empty data.json ---
        with open(data_json_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        logger.info(f"✅ Cleared data file: {data_json_path}")

    except Exception as e:
        logger.error(f"❌ Failed to reset output files: {e}")
        raise