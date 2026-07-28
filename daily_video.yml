"""
トレンド収集モジュール
--------------------------------
著作権に配慮し、スクレイピングではなく各ニュースサイトが公式に配信している
RSSフィードから見出し・概要を取得する。本文全文は取得せず、タイトルと
短い概要のみを使う（これを後段で「要約→言い換え」して独自台本にする）。
"""

import feedparser
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import sys

# 収集対象のRSSフィード。必要に応じて追加・削除してください。
# 各サイトの利用規約でRSS配信は「購読・引用目的」を想定しているため、
# ここでは見出しと要約のみを扱い、全文転載は行わない。
RSS_SOURCES = {
    "NHKニュース": "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "Yahoo!ニュース 主要": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "ITmedia": "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml",
}

MAX_ITEMS_PER_SOURCE = 5


@dataclass
class TrendItem:
    source: str
    title: str
    summary: str
    link: str
    published: str


def fetch_trends() -> list[TrendItem]:
    items: list[TrendItem] = []
    for source_name, url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                print(f"[WARN] {source_name} の取得に失敗しました: {feed.bozo_exception}", file=sys.stderr)
                continue
            for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
                summary = getattr(entry, "summary", "") or ""
                # HTMLタグの簡易除去
                summary = _strip_html(summary)[:200]
                items.append(
                    TrendItem(
                        source=source_name,
                        title=getattr(entry, "title", "").strip(),
                        summary=summary,
                        link=getattr(entry, "link", ""),
                        published=getattr(entry, "published", ""),
                    )
                )
        except Exception as e:
            print(f"[WARN] {source_name} でエラー: {e}", file=sys.stderr)
            continue
    return items


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def save_trends(items: list[TrendItem], path: str = "output/trends.json") -> None:
    data = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "items": [asdict(i) for i in items],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] {len(items)}件のトレンドを {path} に保存しました")


if __name__ == "__main__":
    trends = fetch_trends()
    if not trends:
        print("[ERROR] トレンドを1件も取得できませんでした", file=sys.stderr)
        sys.exit(1)
    save_trends(trends)
