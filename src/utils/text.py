import re

def clamp_len(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n-1]+"…"

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-\.\s]", "", name).strip().replace(" ", "_")
