"""
台本生成モジュール
--------------------------------
収集したトレンド見出し・概要をもとに、Gemini APIでショート動画用の
オリジナル台本（60秒前後）を生成する。

著作権対策として、プロンプトで「原文の言い回しをそのまま使わず、
内容を自分の言葉で要約・解説すること」を明示的に指示している。

トレンド選定は2段階方式:
  1. 複数サイトで似た見出しが出ているものにスコアを付ける（客観的な話題性）
  2. 上位候補をGeminiに見せて、最終的に1件を選ばせる（AIによる質的判断）
"""

import os
import json
import sys
import re
from collections import defaultdict
import google.generativeai as genai

MODEL_NAME = "gemini-3.5-flash-lite"  # 無料枠あり。軽量・高速モデル

SYSTEM_INSTRUCTION = """あなたはショート動画（YouTube Shorts / TikTok想定、60秒程度）の台本作家です。
与えられたニュースの見出しと概要をもとに、視聴者の興味を引く独自の台本を作成してください。

厳守事項:
- 元記事の文章表現をそのまま使わず、必ず自分の言葉で要約・解説すること
- センセーショナルな誇張や誤情報は避け、事実に基づいた内容にすること
- 特定個人への誹謗中傷、差別的表現は含めないこと
- 出力は必ず以下のJSON形式のみ。前置きや説明文は一切付けない

テンポについて（重要）:
- ナレーションは短文を積み重ねてリズムよく。一文は15〜25字程度で区切り、だらだら続けない
- 体言止めや倒置法を適度に使い、間延びしない話し言葉にする
- 「〜です。〜ます。」の単調な繰り返しを避け、語尾にバリエーションをつける
- 例（悪い例）：「今日は東京で大きな雨が降りましたそれによって交通機関に影響が出ています」
- 例（良い例）：「東京、記録的な大雨。交通機関はマヒ状態。一体何が起きているのか？」

出力JSON形式:
{
  "hook": "最初の3秒で惹きつける一言（15字以内）",
  "narration": "ナレーション全文（200〜280字程度、短文を重ねたテンポの良い話し言葉）",
  "captions": [
    {"label": "Point 1のような短い見出し（4〜8字）", "body": "本文の要点（20〜35字程度、体言止めや短文でテンポよく）"}
  ],
  "topic_tag": "動画のトピックを表す短いタグ（10字以内）",
  "image_keywords": ["背景画像を検索するための英単語キーワードを3〜5個。具体的な名詞（例: tokyo street, police officer, hospital, technology, election）"]
}

captionsは5〜7個程度の配列にしてください。各要素はlabelとbodyの2つを持つオブジェクトです。
image_keywordsは必ず英語にしてください（画像検索APIが英語キーワードのみ対応のため）。ニュースの内容を象徴する具体的な情景・物・場所を表す単語にしてください（人名や固有名詞は避け、一般的な情景で表現すること）。
"""

TREND_SELECTION_INSTRUCTION = """あなたはショート動画のネタ選定を行う編集者です。
以下は複数のニュースサイトから収集した見出し一覧です。各項目には「何サイトで同様の話題が
報じられているか」を示す出現回数（count）が付いています。

この情報をもとに、ショート動画（60秒程度）のネタとして最も適した1件を選んでください。
判断基準:
- 出現回数が多い（＝複数サイトで報じられている）ものを優先する
- ただし出現回数が同程度なら、視聴者の興味を引きやすい話題性・意外性のあるものを優先する
- 過度に暗い・扇情的すぎる話題より、幅広い視聴者に受け入れられる話題を優先する

出力は必ず以下のJSON形式のみ。前置きや説明文は一切付けない:
{"selected_index": 選んだ項目のindex番号（整数）}
"""


def _normalize_title(title: str) -> str:
    """見出しの表記ゆれを吸収するための簡易正規化（記号除去・小文字化）。"""
    text = re.sub(r"[【】\[\]（）()「」『』・:：、。\s]", "", title)
    return text.lower()


def _char_ngrams(text: str, n: int = 2) -> set:
    if len(text) < n:
        return {text} if text else set()
    return set(text[i:i + n] for i in range(len(text) - n + 1))


def _title_similarity(a: str, b: str) -> float:
    """2つの正規化済み見出しの類似度を、文字N-gramの重なり具合で計算する（0〜1）。"""
    na, nb = _char_ngrams(a), _char_ngrams(b)
    if not na or not nb:
        return 0.0
    return len(na & nb) / min(len(na), len(nb))


SIMILARITY_THRESHOLD = 0.4


def _score_trends_by_frequency(items: list[dict]) -> list[dict]:
    """似た見出し同士をN-gram類似度でゆるくグルーピングし、
    出現回数をスコアとして各itemに付与する。"""
    normalized = [_normalize_title(item["title"]) for item in items]
    counts = [1] * len(items)

    for i in range(len(items)):
        for j in range(len(items)):
            if i == j:
                continue
            sim = _title_similarity(normalized[i], normalized[j])
            if sim >= SIMILARITY_THRESHOLD:
                counts[i] += 1

    scored = []
    for item, count in zip(items, counts):
        item_copy = dict(item)
        item_copy["_frequency_score"] = count
        scored.append(item_copy)

    return scored


def pick_best_trend(trends_path: str = "output/trends.json", top_n: int = 8) -> dict:
    """
    話題性の高いトレンドを1件選ぶ。
    1. 出現頻度スコアで上位N件に絞り込む
    2. GeminiにそのN件を見せて、最終的に1件を選ばせる
    """
    with open(trends_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    if not items:
        raise RuntimeError("トレンドデータが空です")

    scored_items = _score_trends_by_frequency(items)
    scored_items.sort(key=lambda x: x["_frequency_score"], reverse=True)
    candidates = scored_items[:top_n]

    # Gemini APIキーが無い場合や失敗した場合は、頻度スコア1位をそのまま採用
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or len(candidates) == 1:
        return candidates[0]

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=TREND_SELECTION_INSTRUCTION,
        )
        listing = "\n".join(
            f"{i}. [出現回数:{c['_frequency_score']}] {c['title']} — {c['summary'][:60]}"
            for i, c in enumerate(candidates)
        )
        response = model.generate_content(
            listing,
            generation_config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        idx = int(result.get("selected_index", 0))
        if 0 <= idx < len(candidates):
            print(f"[OK] 話題性判定によりトレンドを選定しました（候補{len(candidates)}件中 index={idx}）")
            return candidates[idx]
    except Exception as e:
        print(f"[WARN] AIによるトレンド選定に失敗、頻度スコア1位を採用します: {e}", file=sys.stderr)

    return candidates[0]


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
