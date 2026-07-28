"""
音声生成モジュール
--------------------------------
無料のgTTS（Google Translate TTS）でナレーション音声を生成する。
音質をもっと上げたい場合は、このファイルの generate_audio() だけを
ElevenLabs / OpenAI TTS 等の呼び出しに差し替えれば良い設計にしている。
"""

import json
import sys
from gtts import gTTS


def generate_audio(text: str, out_path: str = "output/narration.mp3", lang: str = "ja") -> str:
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(out_path)
    print(f"[OK] 音声を {out_path} に保存しました")
    return out_path


def load_script(path: str = "output/script.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    try:
        script = load_script()
        generate_audio(script["narration"])
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
