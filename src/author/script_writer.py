import os, math
from pathlib import Path
from src.utils.io import read_yaml, read_json, write_json
from src.utils.logger import Logger
from src.utils.hash import stable_hash
from src.utils.text import clamp_len
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = """You are a financial news brief writer. 
Write a 58-60s English script for a vertical short.
Constraints:
- Start with a 1-sentence hook (<=16 words).
- Then 3 concise bullet points (facts + why it matters).
- End with neutral CTA: "Follow for more daily market briefs."
- This is an original paraphrase; do NOT quote or read the article verbatim.
- Include a one-line disclaimer: "Not financial advice."
Return JSON with:
{ "title": "...",
  "hook": "...",
  "bullets": ["...","...","..."],
  "cta": "...",
  "subtitle_cues": [ {"t":0.0,"text":"..."}, ... ] } 
Subtitle cues:
- Split into 6-10 chunks across total_duration_sec.
- Punchy, 5-8 words per chunk.
"""

def write_script(raw_item_path: Path, config_path="config.yaml", total_duration_sec=58.0):
    cfg = read_yaml(config_path)
    raw = read_json(raw_item_path)
    log = Logger()
    prompt = f"""Article:
TITLE: {raw['title']}
SUMMARY: {raw['summary']}
LINK: {raw['link']}
Write the brief."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system", "content":SYSTEM},
                  {"role":"user", "content":prompt}],
        temperature=0.5
    )
    txt = resp.choices[0].message.content
    # 모델이 JSON 문자열로 응답한다고 가정(실무에선 json.loads with try/except)
    import json
    data = json.loads(txt)
    # 시간 재배치
    n = max(6, min(10, len(data.get("subtitle_cues",[])) or 8))
    step = total_duration_sec / n
    cues = []
    for i in range(n):
        cues.append({"t": round(i*step,2), "text": data["subtitle_cues"][i % len(data["subtitle_cues"])]["text"]})
    data["subtitle_cues"] = cues
    # 메타
    data["link"] = raw["link"]
    data["title"] = clamp_len(data["title"], 58)
    h = stable_hash(raw["title"]+raw["link"])
    out = raw_item_path.parent / f"{h}.script.json"
    write_json(out, data)
    log.write({"stage":"script","hash":h,"title":data["title"]})
    return out
