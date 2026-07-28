"""
メインパイプライン
--------------------------------
収集 → 台本生成 → 背景画像取得 → 音声生成 → 動画合成 を順番に実行する。
GitHub Actions から `python src/main.py` として毎日呼び出される想定。
"""

import sys
import os
import traceback

os.makedirs("output", exist_ok=True)

from collect_trends import fetch_trends, save_trends
from generate_script import pick_best_trend, generate_script, save_script
from fetch_background import fetch_background_images, save_background_manifest
from generate_audio import generate_audio
from compose_video import compose_video


def run() -> None:
    print("=== 1/5 トレンド収集 ===")
    trends = fetch_trends()
    if not trends:
        raise RuntimeError("トレンドを1件も取得できませんでした")
    save_trends(trends)

    print("=== 2/5 台本生成 ===")
    trend = pick_best_trend()
    script = generate_script(trend)
    save_script(script)
    print(f"  選ばれたトピック: {script.get('topic_tag')}")

    print("=== 3/5 背景画像取得 ===")
    try:
        keywords = script.get("image_keywords", []) or ["news", "city"]
        images = fetch_background_images(keywords)
        if not images:
            print("  [WARN] 背景画像が取得できませんでした。単色背景にフォールバックします")
        save_background_manifest(images)
    except Exception as e:
        # 背景画像の取得に失敗しても、動画生成自体は単色背景で続行する
        print(f"  [WARN] 背景画像取得をスキップします: {e}")
        save_background_manifest([])

    print("=== 4/5 音声生成 ===")
    generate_audio(script["narration"])

    print("=== 5/5 動画合成 ===")
    out_path = compose_video()

    print(f"\n✅ 完了: {out_path}")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("[FATAL ERROR]", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
