"""
メインパイプライン
--------------------------------
収集 → 台本生成 → 音声生成 → 動画合成 を順番に実行する。
GitHub Actions から `python src/main.py` として毎日呼び出される想定。
"""

import sys
import traceback

from collect_trends import fetch_trends, save_trends
from generate_script import pick_best_trend, generate_script, save_script
from generate_audio import generate_audio
from compose_video import compose_video


def run() -> None:
    print("=== 1/4 トレンド収集 ===")
    trends = fetch_trends()
    if not trends:
        raise RuntimeError("トレンドを1件も取得できませんでした")
    save_trends(trends)

    print("=== 2/4 台本生成 ===")
    trend = pick_best_trend()
    script = generate_script(trend)
    save_script(script)
    print(f"  選ばれたトピック: {script.get('topic_tag')}")

    print("=== 3/4 音声生成 ===")
    generate_audio(script["narration"])

    print("=== 4/4 動画合成 ===")
    out_path = compose_video()

    print(f"\n✅ 完了: {out_path}")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        print("[FATAL ERROR]", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
