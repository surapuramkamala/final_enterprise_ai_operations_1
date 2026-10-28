import json
import os
import uuid
from datetime import datetime, timezone

from app.config import TRACE_FILE


def trace(event_type, name, **details):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": details.pop("trace_id", str(uuid.uuid4())),
        "event_type": event_type,
        "name": name,
        "details": details,
    }

    directory = os.path.dirname(TRACE_FILE) or "."
    os.makedirs(directory, exist_ok=True)

    with open(TRACE_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")

    return record


def read_traces(limit=100):
    if not os.path.exists(TRACE_FILE):
        return []

    with open(TRACE_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    results = []

    for line in lines[-max(1, min(limit, 1000)):]:
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return results