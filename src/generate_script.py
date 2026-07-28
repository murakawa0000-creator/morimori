"""
台本生成モジュール
--------------------------------
収集したトレンド見出し・概要をもとに、Gemini APIでショート動画用の
オリジナル台本（60秒前後）を生成する。

著作権対策として、プロンプトで「原文の言い回しをそのまま使わず、
内容を自分の言葉で要約・解説すること」を明示的に指示している。
"""

import os
import json
import sys
import google.generativeai as genai

MODEL_NAME = "gemini-3.5-flash-lite"  # 無料枠あり。最新の軽量モデル

SYSTEM_INSTRUCTION = """あなたはショート動画（YouTube Shorts / TikTok想定、60秒程度）の台本作家です。
与えられたニュースの見出しと概要をもとに、視聴者の興味を引く独自の台本を作成してください。

厳守事項:
- 元記事の文章表現をそのまま使わず、必ず自分の言葉で要約・解説すること
- センセーショナルな誇張や誤情報は避け、事実に基づいた内容にすること
- 特定個人への誹謗中傷、差別的表現は含めないこと
- 出力は必ず以下のJSON形式のみ。前置きや説明文は一切付けない

出力JSON形式:
{
  "hook": "最初の3秒で惹きつける一言（15字以内）",
  "narration": "ナレーション全文（200〜280字程度、話し言葉）",
  "captions": ["字幕として画面に出す短いフレーズを5〜8個の配列で"],
  "topic_tag": "動画のトピックを表す短いタグ（10字以内）"
}
"""


def generate_script(trend_item: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    user_prompt = (
        f"見出し: {trend_item['title']}\n"
        f"概要: {trend_item['summary']}\n"
        f"出典: {trend_item['source']}"
    )

    response = model.generate_content(
        user_prompt,
        generation_config={"response_mime_type": "application/json"},
    )

    try:
        script = json.loads(response.text)
    except json.JSONDecodeError:
        raise RuntimeError(f"台本のJSON解析に失敗しました: {response.text[:300]}")

    script["source_title"] = trend_item["title"]
    script["source_link"] = trend_item.get("link", "")
    return script


def pick_best_trend(trends_path: str = "output/trends.json") -> dict:
    """収集済みトレンドの中から動画化する1件を選ぶ（今回は先頭を採用）。"""
    with open(trends_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    if not items:
        raise RuntimeError("トレンドデータが空です")
    return items[0]


def save_script(script: dict, path: str = "output/script.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"[OK] 台本を {path} に保存しました")


if __name__ == "__main__":
    try:
        trend = pick_best_trend()
        script = generate_script(trend)
        save_script(script)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
