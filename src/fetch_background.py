"""
背景画像取得モジュール
--------------------------------
Pexels API（無料）を使い、台本のimage_keywordsに基づいてニュース関連の
フリー素材写真を検索・ダウンロードする。Pexelsの写真は無料で商用利用も
可能だが、可能な範囲でクレジット表記（撮影者名）を動画内に入れることを推奨する。
"""

import os
import json
import sys
import requests

PEXELS_API_URL = "https://api.pexels.com/v1/search"
DOWNLOAD_DIR = "output/backgrounds"


def fetch_background_images(keywords: list[str], max_images: int = 5) -> list[dict]:
    """
    キーワードのリストから、各キーワードにつき1枚ずつ画像を検索してダウンロードする。
    戻り値は [{"local_path": "...", "photographer": "...", "keyword": "..."}] のリスト。
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 PEXELS_API_KEY が設定されていません")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    headers = {"Authorization": api_key}
    results = []

    for idx, keyword in enumerate(keywords[:max_images]):
        try:
            resp = requests.get(
                PEXELS_API_URL,
                headers=headers,
                params={
                    "query": keyword,
                    "per_page": 1,
                    "orientation": "portrait",  # 縦型ショート動画向け
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            photos = data.get("photos", [])
            if not photos:
                print(f"[WARN] '{keyword}' の画像が見つかりませんでした", file=sys.stderr)
                continue

            photo = photos[0]
            image_url = photo["src"]["large2x"]
            photographer = photo.get("photographer", "Pexels")

            local_path = os.path.join(DOWNLOAD_DIR, f"bg_{idx}.jpg")
            img_resp = requests.get(image_url, timeout=20)
            img_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(img_resp.content)

            results.append(
                {
                    "local_path": local_path,
                    "photographer": photographer,
                    "keyword": keyword,
                }
            )
            print(f"[OK] '{keyword}' → {local_path} (撮影: {photographer})")
        except Exception as e:
            print(f"[WARN] '{keyword}' の取得に失敗: {e}", file=sys.stderr)
            continue

    return results


def load_script(path: str = "output/script.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_background_manifest(images: list[dict], path: str = "output/backgrounds.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2)
    print(f"[OK] 背景画像リストを {path} に保存しました（{len(images)}枚）")


if __name__ == "__main__":
    try:
        script = load_script()
        keywords = script.get("image_keywords", []) or ["news", "city street"]
        images = fetch_background_images(keywords)
        if not images:
            print("[WARN] 背景画像が1枚も取得できませんでした。単色背景にフォールバックします", file=sys.stderr)
        save_background_manifest(images)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
