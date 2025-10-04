from pathlib import Path
import feedparser, random, time
from src.utils.io import write_json
from src.utils.logger import Logger
from src.utils.hash import stable_hash
from src.utils.text import clamp_len

def collect_items(feeds: list, out_dir: Path, limit_per_feed=10):
    log = Logger()
    items = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries[:limit_per_feed]:
            title = e.get("title", "")
            summary = e.get("summary", "") or e.get("description","")
            link = e.get("link","")
            if not title or not link: 
                continue
            items.append({
                "title": clamp_len(title, 140),
                "summary": clamp_len(summary, 400),
                "link": link
            })
    # 난수 셔플 후 상위 6개만
    random.shuffle(items)
    picks = items[:6]
    # 워크아이템 저장
    for it in picks:
        h = stable_hash(it["title"]+it["link"])
        write_json(out_dir / f"{h}.raw.json", it)
        log.write({"stage":"ingest","hash":h,"title":it["title"],"link":it["link"]})
    return picks
