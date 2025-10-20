# processors/schema_processor.py
def modify_schema(ai_outputs):
    """
    Merge and return the schema from AI outputs.
    ai_outputs: list of dicts returned from process_with_bedrock()
    """
    merged_schema = {"mappings": {}, "settings": {}}

    for output in ai_outputs:
        if not isinstance(output, dict):
            continue
        if "schema" in output:
            schema_part = output["schema"]

            # Merge mappings
            if "mappings" in schema_part:
                merged_schema["mappings"].update(schema_part["mappings"])

            # Merge settings
            if "settings" in schema_part:
                merged_schema["settings"].update(schema_part["settings"])

    return merged_schema
