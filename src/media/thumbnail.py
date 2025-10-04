from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from src.utils.io import read_yaml, read_json
from src.utils.text import clamp_len, sanitize_filename

def make_thumbnail(script_path: Path, config_path="config.yaml"):
    cfg = read_yaml(config_path)
    W, H = 1280, 720
    font_path = cfg["video"]["font_path"]
    title = clamp_len(read_json(script_path)["title"], 56)

    img = Image.new("RGB", (W,H), (15,18,24))
    draw = ImageDraw.Draw(img)
    # 배경 그래디언트 느낌
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    # 테두리
    draw.rectangle([(8,8),(W-8,H-8)], outline=(80,200,255), width=6)
    # 텍스트
    fnt = ImageFont.truetype(font_path, 72)
    tw, th = draw.textbbox((0,0), title, font=fnt)[2:]
    draw.text(((W-tw)//2, (H-th)//2), title, fill=(255,255,255), font=fnt)
    out = script_path.parent / f"{sanitize_filename(title)}.jpg"
    img.save(out, "JPEG", quality=95)
    return out
