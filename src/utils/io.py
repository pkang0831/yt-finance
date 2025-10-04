from pathlib import Path
import json, os
from dotenv import load_dotenv
import yaml

load_dotenv()

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_yaml(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def write_json(path: Path, obj: dict):
    ensure_dir(path.parent)
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def read_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)
