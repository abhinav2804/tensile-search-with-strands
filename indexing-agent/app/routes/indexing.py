from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import time
from app.config.config_loader import config
from app.services.indexing_pipeline import (
    fetch_dynamo_data,
    make_file_combos,
    process_file_combos_with_bedrock,
    index_to_elasticsearch
)
from app.utils.logger import logger
from app.utils.file_utils import reset_output_files

router = APIRouter()

def event_stream(user_id: str, data_path: str, user_query_path: str):
    start_time = time.time()
    total_steps = 4
    current_step = 1

    def send_event(step, status, progress, details="", summary=None):
        event_data = {
            "step": step,
            "status": status,
            "progress": round(progress, 2),
            "details": details
        }
        if summary is not None:
            event_data["summary"] = summary
        yield f"data: {json.dumps(event_data)}\n\n"

    try:
        #Step 0: Start
        yield from send_event("Start", "in_progress", 0, "Indexing process started")
        reset_output_files(config, user_id)
        
        # Step 1: DynamoDB
        yield from send_event("Fetching data from DynamoDB", "in_progress", (current_step/total_steps)*100)
        user_data = fetch_dynamo_data(user_id, config)
        current_step += 1
        yield from send_event("Fetching data from DynamoDB", "completed", (current_step/total_steps)*100, f"Fetched {len(user_data)} items")

        # Step 2: Make file combos
        yield from send_event("Preparing file combos", "in_progress", (current_step/total_steps)*100)
        file_combos = make_file_combos(data_path, user_query_path)
        yield from send_event("Preparing file combos", "completed", (current_step/total_steps)*100, f"Prepared {len(file_combos)} combos")
        current_step += 1
        
        # Step 3: Process combos with Bedrock
        yield from send_event("Processing combos with AWS Bedrock", "in_progress", (current_step/total_steps)*100)
        process_file_combos_with_bedrock(file_combos, config, user_id)
        yield from send_event("Processing combos with AWS Bedrock", "completed", (current_step/total_steps)*100, f"Processed Model items")
        current_step += 1

        # Step 4: Elasticsearch indexing
        yield from send_event("Indexing to Elasticsearch", "in_progress", (current_step/total_steps)*100)
        index_name, len_of_docs = index_to_elasticsearch(
            config,
            user_id,
            dynamo_data=user_data
        )
        yield from send_event("Indexing to Elasticsearch", "completed", 100, f"Index '{index_name}' created & data indexed ✅")

        # Summary
        time_taken = round(time.time() - start_time, 2)
        summary_data = {
            "message": "🎉 All done! Your data is now searchable.",
            "total_documents": len_of_docs,
            "index_name": index_name,
            "time_taken_seconds": time_taken
        }
        yield from send_event("Summary", "completed", 100, "Process completed", summary=summary_data)

    except Exception as e:
        logger.error("Error during indexing process", exc_info=True)
        yield f"data: {json.dumps({'step': 'Error', 'status': 'failed', 'progress': None, 'details': str(e)})}\n\n"

@router.get("/triggerIndexingLive")
def trigger_indexing_live(user_id: str, data_path: str, user_query_path: str):
    return StreamingResponse(event_stream(user_id, data_path, user_query_path),
                              media_type="text/event-stream")
