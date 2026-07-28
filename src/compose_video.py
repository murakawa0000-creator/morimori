"""
動画合成モジュール
--------------------------------
台本(script.json)・音声(narration.mp3)・背景画像(backgrounds.json)から、
縦型ショート動画(1080x1920)を自動合成する。

背景: Pexelsから取得した写真を「拡大+ぼかし+暗めオーバーレイ」でフルスクリーン
      敷き詰め、写真が無い場合は単色背景にフォールバックする。
字幕: 「Point 1」のような赤い見出しラベル + 白背景の本文、という
      2段構成のテロップを画面中央に表示する。
"""

import json
import sys
import os
from PIL import Image, ImageFilter
from moviepy import (
    AudioFileClip,
    ColorClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
)

WIDTH, HEIGHT = 1080, 1920
FONT_PATH = os.environ.get(
    "JP_FONT_PATH",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)
FONT_PATH_BOLD = os.environ.get(
    "JP_FONT_PATH_BOLD",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)

# 背景写真が1枚も無い場合のフォールバック単色
BG_COLORS = ["#1B1B2F", "#16213E", "#2B2D42", "#22223B"]

PROCESSED_BG_DIR = "output/backgrounds_processed"


def _prepare_background_image(src_path: str, out_path: str) -> str:
    """写真を1080x1920にトリミング+軽くぼかし+暗めのオーバーレイをかけて保存する。
    字幕を乗せても読みやすくするための前処理。"""
    img = Image.open(src_path).convert("RGB")

    target_ratio = WIDTH / HEIGHT
    img_ratio = img.width / img.height
    if img_ratio > target_ratio:
        new_height = HEIGHT
        new_width = int(new_height * img_ratio)
    else:
        new_width = WIDTH
        new_height = int(new_width / img_ratio)
    img = img.resize((new_width, new_height))

    left = (new_width - WIDTH) // 2
    top = (new_height - HEIGHT) // 2
    img = img.crop((left, top, left + WIDTH, top + HEIGHT))

    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    overlay = Image.new("RGB", img.size, (0, 0, 0))
    img = Image.blend(img, overlay, alpha=0.35)

    img.save(out_path, quality=90)
    return out_path


def build_background_clips(
    duration: float, background_images: list[dict], topic_tag: str = ""
) -> list:
    """背景画像を時間で切り替えながら表示するクリップ列を作る。
    画像が無ければ単色背景にフォールバックする。"""
    if not background_images:
        color_idx = abs(hash(topic_tag)) % len(BG_COLORS)
        hex_color = BG_COLORS[color_idx]
        rgb = tuple(int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        return [ColorClip(size=(WIDTH, HEIGHT), color=rgb, duration=duration)]

    os.makedirs(PROCESSED_BG_DIR, exist_ok=True)
    n = len(background_images)
    per_image = duration / n
    clips = []
    t = 0.0
    for idx, bg in enumerate(background_images):
        processed_path = os.path.join(PROCESSED_BG_DIR, f"processed_{idx}.jpg")
        try:
            _prepare_background_image(bg["local_path"], processed_path)
            clip = (
                ImageClip(processed_path)
                .with_start(t)
                .with_duration(per_image)
            )
            clips.append(clip)
        except Exception as e:
            print(f"[WARN] 背景画像の処理に失敗（{bg.get('local_path')}）: {e}", file=sys.stderr)
        t += per_image

    if not clips:
        return [ColorClip(size=(WIDTH, HEIGHT), color=(27, 27, 47), duration=duration)]

    return clips


def _make_caption_pair(label: str, body: str, box_width: int) -> CompositeVideoClip:
    """「Point 1」のような赤い見出しラベル + 白背景の本文を1つのクリップとして合成する。"""
    label_clip = TextClip(
        text=label,
        font=FONT_PATH_BOLD,
        font_size=52,
        color="white",
        bg_color="#D8261D",
        method="caption",
        size=(box_width, None),
        text_align="center",
        margin=(20, 14),
    )

    body_clip = TextClip(
        text=body,
        font=FONT_PATH,
        font_size=46,
        color="#1A1A1A",
        bg_color="white",
        method="caption",
        size=(box_width, None),
        text_align="center",
        margin=(24, 18),
    )

    label_h = label_clip.h
    body_clip = body_clip.with_position((0, label_h))

    total_h = label_h + body_clip.h
    combined = CompositeVideoClip(
        [label_clip.with_position((0, 0)), body_clip],
        size=(box_width, total_h),
    )
    return combined


def build_caption_clips(captions: list[dict], hook: str, duration: float) -> list:
    clips = []
    box_width = WIDTH - 140

    hook_clip = (
        TextClip(
            text=hook,
            font=FONT_PATH_BOLD,
            font_size=76,
            color="white",
            stroke_color="black",
            stroke_width=8,
            size=(box_width, None),
            method="caption",
            text_align="center",
        )
        .with_position(("center", 160))
        .with_start(0)
        .with_duration(min(3.0, duration))
    )
    clips.append(hook_clip)

    remaining = max(duration - 3.0, 1.0)
    per_caption = remaining / max(len(captions), 1)
    t = 3.0
    for cap in captions:
        label = cap.get("label", "")
        body = cap.get("body", "")
        pair_clip = _make_caption_pair(label, body, box_width)
        pair_clip = (
            pair_clip.with_position(("center", "center"))
            .with_start(t)
            .with_duration(per_caption)
        )
        clips.append(pair_clip)
        t += per_caption

    return clips


def load_background_manifest(path: str = "output/backgrounds.json") -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compose_video(
    script_path: str = "output/script.json",
    audio_path: str = "output/narration.mp3",
    background_manifest_path: str = "output/backgrounds.json",
    out_path: str = "output/short_video.mp4",
) -> str:
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    background_images = load_background_manifest(background_manifest_path)
    backgrounds = build_background_clips(duration, background_images, script.get("topic_tag", ""))
    captions = build_caption_clips(script["captions"], script["hook"], duration)

    video = CompositeVideoClip([*backgrounds, *captions], size=(WIDTH, HEIGHT))
    video = video.with_audio(audio)
    video = video.with_duration(duration)

    video.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
    )
    print(f"[OK] 動画を {out_path} に保存しました（{duration:.1f}秒）")
    return out_path


if __name__ == "__main__":
    try:
        compose_video()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
