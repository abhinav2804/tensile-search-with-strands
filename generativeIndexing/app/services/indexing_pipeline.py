import os
import json
from itertools import cycle
from app.services.dynamo_db_service import get_user_data
from app.utils.file_utils import detect_file_type, read_structured_file, read_file_in_chunks
from app.utils.logger import logger
from app.services.bedrock_model_service import process_with_bedrock
from app.processors.schema_processor import modify_schema
from app.services.elasticsearch_service import create_index_and_insert

def fetch_dynamo_data(user_id, config):
    return get_user_data(user_id, config)

def make_file_combos(data_path, query_path):
    """
    Create combos of file paths: (data_file, query_file)
    - No duplicate data files
    - Query file can repeat if fewer than data files
    """
    def list_files(path):
        files = []
        if os.path.isdir(path):
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                if os.path.isfile(fpath):
                    files.append(fpath)
        else:
            files.append(path)
        return files

    data_files = list_files(data_path)
    query_files = list_files(query_path)

    combos = []
    query_cycle = cycle(query_files)  # repeat queries if fewer
    for data_file in data_files:
        combos.append((data_file, next(query_cycle)))

    return combos

def process_file_combos_with_bedrock(file_combos, config, user_id):
    bedrock_prompt = config["aws"]["bedrock"].get("prompt", "")

    # Base output dir for this user
    user_output_dir = os.path.join(config["files"]["output_directory"], str(user_id))
    os.makedirs(user_output_dir, exist_ok=True)

    for data_file, query_file in file_combos:
        logger.info(f"📄 Reading data file: {data_file}")
        logger.info(f"📄 Reading query file: {query_file}")

        # --- Read data file ---
        data_type = detect_file_type(data_file)
        data_chunks = list(
            read_structured_file(data_file) if data_type != "unknown"
            else read_file_in_chunks(data_file, config["app"]["chunk_size"])
        )

        # --- Read query file ---
        query_type = detect_file_type(query_file)
        query_chunks = list(
            read_structured_file(query_file) if query_type != "unknown"
            else read_file_in_chunks(query_file, config["app"]["chunk_size"])
        )

        logger.info(
            f"⚙️ Processing data file: {data_file} ({len(data_chunks)} chunks), "
            f"query file: {query_file} ({len(query_chunks)} chunks)"
        )

        # --- Paths ---
        schema_path = os.path.join(user_output_dir, "schema.json")
        readme_path = os.path.join(user_output_dir, "readme.txt")
        data_json_path = os.path.join(user_output_dir, "data.json")

        # --- Load existing schema ---
        schema_data = None
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                try:
                    schema_data = json.load(f)
                except json.JSONDecodeError:
                    schema_data = None

        # --- Load existing readme ---
        readme_data = None
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_data = f.read()

        payload = {
            "docs": data_chunks,
            "queries": query_chunks,
            "schema": schema_data,
            "prompt": bedrock_prompt,
            "readme": readme_data
        }

        # --- Call Bedrock ---
        result = process_with_bedrock(payload, config)
        logger.info(f"✅ Received Bedrock response for {data_file}")

        # Normalize result to list of dicts
        if isinstance(result, dict):
            result_list = [result]
        elif isinstance(result, list):
            result_list = result
        else:
            result_list = []

        # --- Manage Schema ---
        new_schema = modify_schema(result_list)
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(new_schema, f, indent=2)

        # --- Manage Readme ---
        readme_content = next(
            (item.get("readme", "No readme provided") for item in result_list if isinstance(item, dict) and "readme" in item),
            "No readme provided"
        )

        # Save readme in plain text for readability
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # --- Manage Docs ---
        if os.path.exists(data_json_path):
            with open(data_json_path, "r", encoding="utf-8") as f:
                try:
                    all_docs = json.load(f)
                except json.JSONDecodeError:
                    all_docs = []
        else:
            all_docs = []

        new_docs = [
            doc for item in result_list
            if isinstance(item, dict) and "docs" in item
            for doc in item["docs"]
        ]

        all_docs.extend(new_docs)
        with open(data_json_path, "w", encoding="utf-8") as f:
            json.dump(all_docs, f, indent=2)

def index_to_elasticsearch(config, user_id, dynamo_data=None):
    return create_index_and_insert(
        config,
        user_id,
        dynamo_data=dynamo_data
    )
