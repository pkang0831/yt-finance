import os, requests, random
from pathlib import Path
from src.utils.io import read_yaml
from src.utils.logger import Logger

def fetch_broll(keywords: list, out_dir: Path, min_height=1920):
    key = os.getenv("PEXELS_API_KEY"); assert key
    headers = {"Authorization": key}
    q = random.choice(keywords)
    params = {"query": q, "per_page": 10, "orientation":"portrait"}
    r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=25)
    r.raise_for_status()
    vids = r.json().get("videos", [])
    # 높이 기준 가장 큰 파일 선택
    best = None; best_url=None
    for v in vids:
        for f in v.get("video_files", []):
            if f.get("height", 0) >= min_height:
                if (not best) or f["height"]>best.get("height",0):
                    best = f; best_url = f["link"]
    if not best_url and vids:
        best_url = vids[0]["video_files"][0]["link"]
    if not best_url:
        raise RuntimeError("No b-roll found")
    raw = requests.get(best_url, timeout=60)
    raw.raise_for_status()
    path = out_dir / "broll.mp4"
    with open(path, "wb") as f: f.write(raw.content)
    Logger().write({"stage":"broll","keyword":q,"path":str(path)})
    return path
