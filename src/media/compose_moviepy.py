from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, ColorClip, vfx
from pathlib import Path
from src.utils.io import read_yaml, read_json
from src.utils.text import sanitize_filename
from src.utils.logger import Logger

def render_vertical(script_path: Path, broll_path: Path, mp3_path: Path, config_path="config.yaml"):
    cfg = read_yaml(config_path)
    W, H = cfg["video"]["size"]["width"], cfg["video"]["size"]["height"]
    margin = cfg["video"]["margin"]
    font = cfg["video"]["font_path"]
    sub_fs = cfg["video"]["subtitle_font_size"]

    script = read_json(script_path)
    title = script["title"]
    cues = script["subtitle_cues"]

    # 미디어 로드
    v = VideoFileClip(str(broll_path)).resize(height=H).fx(vfx.resize, height=H)
    v = v.crop(width=W, height=H, x_center=v.w/2, y_center=v.h/2)
    a = AudioFileClip(str(mp3_path))
    dur = min(a.duration, 60)  # ≤60초
    v = v.set_duration(dur).without_audio()
    # 오디오 러프 라우드니스: moviepy 기본(정밀 LUFS는 ffmpeg필요)
    a = a.set_duration(dur)

    # 반투명 하단 자막 배경
    bg = ColorClip(size=(W, H), color=(0,0,0)).set_opacity(0)  # 투명
    clips = [v]

    # 자막 오버레이
    per = dur / max(1,len(cues))
    for i, cue in enumerate(cues):
        t = min(cue["t"], dur-0.1)
        end = min(t+per, dur)
        txt = TextClip(cue["text"], fontsize=sub_fs, font=font, color="white", method="caption", size=(W-2*margin,None), align="center")
        txt = txt.set_position(("center", H - 300)).set_start(t).set_duration(end - t)
        # 반투명 바
        bar = ColorClip(size=(W, 220), color=(0,0,0)).set_opacity(0.3).set_position(("center", H - 320)).set_start(t).set_duration(end - t)
        clips += [bar, txt]

    comp = CompositeVideoClip([*clips]).set_audio(a)
    safe_name = sanitize_filename(title) or "market_brief"
    out = script_path.parent / f"{safe_name}.mp4"
    comp.write_videofile(str(out), fps=30, codec="libx264", audio_codec="aac", threads=4, preset="medium")
    Logger().write({"stage":"render","file":str(out)})
    return out
