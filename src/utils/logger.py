import json, os, datetime as dt
from pathlib import Path

class Logger:
    def __init__(self, log_dir="data/logs"):
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d")
        self.path = Path(log_dir) / f"run_{ts}.jsonl"

    def write(self, event: dict):
        event["ts"] = dt.datetime.utcnow().isoformat()+"Z"
        with open(self.path, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False)+"\n")
