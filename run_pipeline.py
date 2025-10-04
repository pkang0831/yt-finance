import os, sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

from src.utils.io import read_yaml, ensure_dir
from src.ingest.news_feed import collect_items
from src.author.script_writer import write_script
from src.voice.tts_elevenlabs import tts
from src.media.broll_pexels import fetch_broll
from src.media.compose_moviepy import render_vertical
from src.media.thumbnail import make_thumbnail
from src.publish.youtube_upload import upload

def main(n_items=None):
    load_dotenv()
    cfg = read_yaml("config.yaml")
    day_dir = Path("data/outputs") / datetime.now().strftime("%Y%m%d_%H%M")
    ensure_dir(day_dir)
    work_dir = Path("data/workitems"); ensure_dir(work_dir)

    # 1) 수집
    items = collect_items(cfg["feeds"], work_dir)
    if n_items: items = items[:int(n_items)]

    made = 0
    for raw in tqdm(items, desc="workitems"):
        from src.utils.hash import stable_hash
        h = stable_hash(raw["title"]+raw["link"])
        raw_path = work_dir / f"{h}.raw.json"
        # 2) 스크립트
        script_path = write_script(raw_path, total_duration_sec=cfg["video"]["target_seconds"])
        # 3) 음성
        mp3_path = tts(script_path)
        # 4) B-roll
        broll_path = fetch_broll(cfg["broll"]["search_terms"], day_dir, min_height=cfg["broll"]["min_height"])
        # 5) 합성
        video_path = render_vertical(script_path, broll_path, mp3_path)
        # 6) 썸네일
        thumb_path = make_thumbnail(script_path)
        # 7) 업로드
        res = upload(video_path, script_path, thumb_path)
        made += 1 if res.get("status")=="ok" else 0

        if made >= cfg["runtime"]["max_items_per_run"]:
            break

if __name__ == "__main__":
    n = sys.argv[1] if len(sys.argv)>1 else None
    main(n_items=n)
