# app/config/config_loader.py
import os
import yaml

def load_secrets(secret_file="keys/secret.key"):
    """
    Reads a simple key=value secret file and returns a dict.
    Lines starting with '#' are ignored.
    """
    secrets = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, secret_file)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Secret file not found at {path}")

    with open(path, "r") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                secrets[key.strip()] = value.strip()
    return secrets

def load_config(filename="config.yaml", secret_file="keys/secret.key"):
    """
    Loads YAML config and merges secrets from secret_file.
    Also dynamically builds DynamoDB base_url from host+port.
    """
    # ✅ Get the absolute path to config.yaml
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")

    with open(path, "r") as file:
        config_data = yaml.safe_load(file)

    # ✅ Load secrets
    secrets = load_secrets(secret_file)

    # ✅ Merge Elasticsearch secrets
    if "elasticsearch" in config_data:
        config_data["elasticsearch"]["host"] = secrets.get("ELASTICSEARCH_HOST", config_data["elasticsearch"]["host"])
        config_data["elasticsearch"]["port"] = int(secrets.get("ELASTICSEARCH_PORT", config_data["elasticsearch"]["port"]))
        config_data["elasticsearch"]["username"] = secrets.get("ELASTICSEARCH_USER", config_data["elasticsearch"]["username"])
        config_data["elasticsearch"]["password"] = secrets.get("ELASTICSEARCH_PASSWORD", config_data["elasticsearch"]["password"])
        if "ELASTICSEARCH_SSL_VERIFY" in secrets:
            config_data["elasticsearch"]["ssl_verify"] = secrets["ELASTICSEARCH_SSL_VERIFY"].lower() == "true"

    # ✅ Merge AWS DynamoDB secrets and build URL
    if "aws" in config_data and "dynamodb" in config_data["aws"]:
        dynamodb_host = secrets.get("AWS_DYNAMODB_HOST")
        dynamodb_port = secrets.get("AWS_DYNAMODB_PORT")
        config_data["aws"]["dynamodb"]["table_name"] = secrets.get("AWS_DYNAMODB_TABLE", config_data["aws"]["dynamodb"]["table_name"])

        # Build base_url if host and port exist
        if dynamodb_host and dynamodb_port:
            # Always use HTTPS for DynamoDB
            config_data["aws"]["dynamodb"]["base_url"] = f"https://{dynamodb_host}:{dynamodb_port}"

    # ✅ Merge AWS Bedrock secrets
    if "aws" in config_data and "bedrock" in config_data["aws"]:
        config_data["aws"]["bedrock"]["model_id"] = secrets.get("AWS_BEDROCK_MODEL_ID", config_data["aws"]["bedrock"]["model_id"])
        config_data["aws"]["bedrock"]["endpoint_url"] = secrets.get("AWS_BEDROCK_ENDPOINT_URL", config_data["aws"]["bedrock"]["endpoint_url"])

    # ✅ Create local directories
    current_dir = os.getcwd()
    output_dir_path = os.path.join(current_dir, "output_dir")
    input_dir_path = os.path.join(current_dir, "input_dir")
    os.makedirs(output_dir_path, exist_ok=True)
    os.makedirs(input_dir_path, exist_ok=True)

    if "files" not in config_data:
        config_data["files"] = {}
    config_data["files"]["output_directory"] = output_dir_path
    config_data["files"]["data_directory"] = input_dir_path

    return config_data


# ✅ Load config once, globally accessible
config = load_config()
