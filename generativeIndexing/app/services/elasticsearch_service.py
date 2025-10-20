# services/elasticsearch_service.py
import os
import json
import ijson
from datetime import datetime
from elasticsearch import Elasticsearch, helpers
from app.utils.logger import logger
from app.services.bedrock_model_service import call_bedrock_model

def json_stream_parser(file_obj):
    """Parse large JSON arrays without loading all into memory."""
    for item in ijson.items(file_obj, "item"):
        yield item

def get_ai_index_name(config, schema, fields_info):
    """
    Use Bedrock Claude to suggest a unique, relevant Elasticsearch index name.
    Prompt is read directly from config["elasticsearch"]["prompt"].
    """
    prompt = config.get("elasticsearch", {}).get("prompt")

    if not prompt:
        raise ValueError("Elasticsearch prompt is missing in config['elasticsearch']['prompt']")

    # Format the prompt with provided schema, sample data, and user input
    prompt = prompt.format(
        schema=json.dumps(schema, indent=2),
        sample_data=json.dumps(fields_info, indent=2),
    )

    raw_output = call_bedrock_model(prompt, config, parse_json=False)

    if not raw_output:
        return config["elasticsearch"]["default_index"]

    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict) and "name" in parsed:
            return parsed["name"].strip()
        elif isinstance(parsed, str):
            return parsed.strip()
    except json.JSONDecodeError:
        return raw_output.strip()


def create_index_and_insert(config, user_id, dynamo_data=None):
    """
    Create Elasticsearch index and bulk insert data in a memory-safe manner.
    Returns (index_name, docs_indexed_count)
    """

    safe_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # --- Host/Port setup ---
    host = dynamo_data.get("es_host") if dynamo_data else None
    port = dynamo_data.get("es_port") if dynamo_data else None
    host = host or config["elasticsearch"]["host"]
    port = port or config["elasticsearch"]["port"]
    scheme = config["elasticsearch"].get("scheme", "http")

    es = Elasticsearch(
        hosts=[{"host": host, "port": int(port), "scheme": scheme}],
        http_auth=(
            config["elasticsearch"]["username"],
            config["elasticsearch"]["password"]
        ),
        verify_certs=config["elasticsearch"]["ssl_verify"]
    )

    if not es.ping():
        logger.error("❌ Elasticsearch is not reachable")
        raise ConnectionError("Elasticsearch down")
    logger.info("✅ Elasticsearch is healthy")

    # --- User-specific output directory ---
    user_output_dir = os.path.join(config["files"]["output_directory"], str(user_id))
    os.makedirs(user_output_dir, exist_ok=True)

    # --- Prepare schema ---
    schema_path = os.path.join(user_output_dir, "schema.json")
    schema = None
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            try:
                schema = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ schema.json is invalid JSON, using empty schema")
                schema = None

    # --- Readme file ---
    readme_path = os.path.join(user_output_dir, "readme.txt")
    fields_info = None
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            fields_info = f.read()

    # --- Index naming ---
    if schema and fields_info:
        index_name = get_ai_index_name(config, schema, fields_info)
        logger.info(f"📌 AI Suggested Index Name: {index_name}")
    else:
        index_name = config["elasticsearch"]["default_index"] + safe_timestamp
        logger.info(f"📌 Using default index name: {index_name}")

    # --- Create index ---
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body={"mappings": {"properties": schema or {}}})
        logger.info(f"✅ Created Elasticsearch index: {index_name}")
    else:
        logger.warning(f"⚠️ Index already exists: {index_name}")
        index_name = f"{index_name.lower()}_{safe_timestamp}"
        es.indices.create(index=index_name, body={"mappings": {"properties": schema or {}}})
        logger.info(f"✅ Created Elasticsearch index: {index_name}")

    # --- Stream documents & count ---
    data_json_path = os.path.join(user_output_dir, "data.json")
    docs_indexed_count = 0

    def doc_generator():
        nonlocal docs_indexed_count
        if os.path.exists(data_json_path):
            with open(data_json_path, "r", encoding="utf-8") as f:
                try:
                    for doc in ijson.items(f, "item"):  # parses large JSON array
                        docs_indexed_count += 1
                        yield {
                            "_index": index_name,
                            "_source": doc
                        }
                except Exception as e:
                    logger.error(f"❌ Error reading data.json: {e}")

    helpers.bulk(es, doc_generator())

    logger.info(f"📥 Bulk inserted {docs_indexed_count} documents into index {index_name}")
    return index_name, docs_indexed_count
