"""
Minimal logging layer (v1). Appends one JSON line per pipeline run
to logs/pipeline_log.jsonl. Swap for a Postgres table later —
see architecture doc section 4.
"""
import json
import os
import time
import uuid

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline_log.jsonl")


def log_run(entry: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry["request_id"] = entry.get("request_id", str(uuid.uuid4()))
    entry["timestamp"] = entry.get("timestamp", time.time())

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_logs(limit: int = 20):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE) as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-limit:]]


if __name__ == "__main__":
    log_run({"raw_query": "test", "success": True})
    print(read_logs())