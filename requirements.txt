"""
動画合成モジュール
--------------------------------
台本(script.json)と音声(narration.mp3)から、縦型ショート動画(1080x1920)を
自動合成する。映像は「単色背景+アニメーションする字幕」のテキストモーション
中心の構成（案A）。将来的に写真素材やAI生成映像に差し替える場合は、
build_background_clip() の中身だけを差し替えればよい設計にしている。
"""

import json
import sys
import os
from moviepy import (
    AudioFileClip,
    ColorClip,
    TextClip,
    CompositeVideoClip,
)

WIDTH, HEIGHT = 1080, 1920
FONT_PATH = os.environ.get(
    "JP_FONT_PATH",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)

# 背景色は数トピックで簡易的に切り替え、単調にならないようにする
BG_COLORS = ["#1B1B2F", "#16213E", "#2B2D42", "#22223B"]


def build_background_clip(duration: float, topic_tag: str = "") -> ColorClip:
    color_idx = abs(hash(topic_tag)) % len(BG_COLORS)
    hex_color = BG_COLORS[color_idx]
    rgb = tuple(int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return ColorClip(size=(WIDTH, HEIGHT), color=rgb, duration=duration)


def build_caption_clips(captions: list[str], hook: str, duration: float) -> list[TextClip]:
    clips = []

    # フック（冒頭3秒、大きく強調）
    hook_clip = (
        TextClip(
            text=hook,
            font=FONT_PATH,
            font_size=90,
            color="white",
            stroke_color="black",
            stroke_width=8,
            size=(WIDTH - 120, None),
            method="caption",
            text_align="center",
        )
        .with_position(("center", "center"))
        .with_start(0)
        .with_duration(min(3.0, duration))
    )
    clips.append(hook_clip)

    # 残り時間をキャプション数で等分して順番に表示
    remaining = max(duration - 3.0, 1.0)
    per_caption = remaining / max(len(captions), 1)
    t = 3.0
    for cap in captions:
        clip = (
            TextClip(
                text=cap,
                font=FONT_PATH,
                font_size=64,
                color="white",
                stroke_color="black",
                stroke_width=6,
                size=(WIDTH - 160, None),
                method="caption",
                text_align="center",
            )
            .with_position(("center", "center"))
            .with_start(t)
            .with_duration(per_caption)
        )
        clips.append(clip)
        t += per_caption

    return clips


def compose_video(
    script_path: str = "output/script.json",
    audio_path: str = "output/narration.mp3",
    out_path: str = "output/short_video.mp4",
) -> str:
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    background = build_background_clip(duration, script.get("topic_tag", ""))
    captions = build_caption_clips(script["captions"], script["hook"], duration)

    video = CompositeVideoClip([background, *captions], size=(WIDTH, HEIGHT))
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
