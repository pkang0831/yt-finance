import os, requests
from pathlib import Path
from src.utils.io import read_json
from src.utils.logger import Logger
from src.utils.hash import stable_hash

ELEVEN_API = "https://api.elevenlabs.io/v1/text-to-speech"

def tts(script_path: Path, voice_id=None, out_dir=None):
    api_key = os.getenv("ELEVEN_API_KEY")
    voice_id = voice_id or os.getenv("ELEVEN_VOICE_ID")
    assert api_key and voice_id, "ELEVEN API KEY/VOICE_ID required"
    data = read_json(script_path)
    text = f"{data['hook']} " + " ".join(data['bullets']) + f" {data['cta']} Not financial advice."
    payload = {
      "text": text,
      "model_id": "eleven_multilingual_v2",
      "voice_settings": {"stability":0.5, "similarity_boost":0.75}
    }
    headers = {"xi-api-key": api_key, "accept":"audio/mpeg","content-type":"application/json"}
    r = requests.post(f"{ELEVEN_API}/{voice_id}", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    h = stable_hash(data["title"]+data["link"])
    out_dir = out_dir or script_path.parent
    mp3 = Path(out_dir) / f"{h}.voice.mp3"
    with open(mp3, "wb") as f: f.write(r.content)
    Logger().write({"stage":"tts","hash":h,"mp3":str(mp3)})
    return mp3
