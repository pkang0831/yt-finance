import os, json, hashlib
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from src.utils.io import read_yaml
from src.utils.text import clamp_len
from src.utils.hash import stable_hash
from src.utils.logger import Logger

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def _get_creds():
    client_path = os.getenv("YT_CLIENT_SECRET_PATH")
    token_path = os.getenv("YT_TOKEN_PATH")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds

def _hash_for_dedupe(title: str, link: str) -> str:
    return stable_hash(title + "|" + link)

def upload(video_path: Path, script_path: Path, thumb_path: Path, config_path="config.yaml"):
    cfg = read_yaml(config_path)
    data = json.load(open(script_path))
    dedupe = _hash_for_dedupe(data["title"], data["link"])
    # 중복 방지 파일
    dedb = Path("data/outputs/dedup.json")
    seen = json.load(open(dedb)) if dedb.exists() else {}
    if dedupe in seen:
        Logger().write({"stage":"upload","skipped":"duplicate","title":data["title"]})
        return {"status":"skipped-duplicate"}
    # 메타
    title = clamp_len(data["title"], 58)
    desc = f"{data['hook']}\n- " + "\n- ".join(data["bullets"]) + f"\n\n{cfg['upload']['disclaimer']}\nSource: summarized & paraphrased."
    tags = cfg["upload"]["default_tags"]
    categoryId = os.getenv("YT_DEFAULT_CATEGORY_ID","25")
    privacyStatus = cfg["upload"]["privacy_status"]

    creds = _get_creds()
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "categoryId": categoryId,
            "tags": tags
        },
        "status": {"privacyStatus": privacyStatus}
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    video_id = resp["id"]
    # 썸네일
    yt.thumbnails().set(videoId=video_id, media_body=str(thumb_path)).execute()

    # 중복 등록
    seen[dedupe] = {"title": title, "video_id": video_id}
    with open(dedb, "w") as f: json.dump(seen, f, indent=2)
    Logger().write({"stage":"upload","video_id":video_id,"title":title})
    return {"status":"ok","video_id":video_id}
