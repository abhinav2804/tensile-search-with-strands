# services/bedrock_service.py
import json
import boto3
import re
from app.utils.logger import logger

def call_bedrock_model(prompt, config, parse_json=False):
    client = boto3.client("bedrock-runtime", region_name=config["aws"]["region"])

    try:
        response = client.invoke_model(
            modelId=config["aws"]['bedrock']["model_id"],
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": config["aws"]['bedrock'].get("max_tokens", 1000),
                "temperature": config["aws"]['bedrock'].get("temperature", 0.7),
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        )

        raw_output = response["body"].read().decode()

        try:
            bedrock_data = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode Bedrock JSON: {e}")
            return raw_output

        logger.info("📥 Received structured response from Bedrock model")

        try:
            model_text = bedrock_data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"❌ Unexpected Bedrock response format: {e}")
            return bedrock_data

        if parse_json:
            # Remove markdown fences
            cleaned_text = re.sub(r"^```(?:json)?", "", model_text.strip())
            cleaned_text = re.sub(r"```$", "", cleaned_text.strip())

            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Model output is not valid JSON ({e}), returning raw cleaned text")
                return cleaned_text

        return model_text

    except Exception as e:
        logger.error(f"❌ Bedrock model invocation failed: {e}")
        return None


def process_with_bedrock(payload, config):
    """
    Process a batch of documents & queries with AWS Bedrock.
    """
    docs_str = json.dumps(payload.get("docs", []), indent=2)
    queries_str = json.dumps(payload.get("queries", []), indent=2)
    schema_str = json.dumps(payload.get("schema", {}), indent=2) if payload.get("schema") else "No schema provided"
    readme_str = payload.get("readme", "No readme provided")

    parts = []

    if payload.get("prompt"):
        parts.append(payload["prompt"])

    parts.append("Respond with JSON output containing processed document data.")

    if schema_str:
        parts.append(f"Schema: {schema_str}")
    if queries_str:
        parts.append(f"User Queries: {queries_str}")
    if docs_str:
        parts.append(f"Documents: {docs_str}")
    if readme_str:
        parts.append(f"Readme: {readme_str}")

    prompt = "\n".join(parts)

    logger.info(
        f"📤 Sending batch to Bedrock model: {config['aws']['bedrock']['model_id']} "
        f"with {len(payload.get('docs', []))} docs and {len(payload.get('queries', []))} queries\n"
    )

    return call_bedrock_model(prompt, config, parse_json=True)
