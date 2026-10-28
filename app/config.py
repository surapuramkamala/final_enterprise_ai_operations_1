import os
from dotenv import load_dotenv

load_dotenv()

TRACE_FILE = os.getenv(
    "TRACE_FILE",
    "./data/traces.jsonl"
)