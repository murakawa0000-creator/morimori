# トレンド自動ショート動画生成ツール

ニュースRSSから話題を収集し、Gemini APIで独自台本を生成、無料TTSでナレーションを
作成し、縦型ショート動画（1080x1920, mp4）を毎日自動で作るツールです。
GitHub Actionsで完全無料〜低コストで毎日自動実行されます。

## 全体の流れ

```
RSS収集 → Gemini APIで独自台本生成 → gTTSでナレーション音声 → moviepyで動画合成
```

1. `src/collect_trends.py` … 複数のニュースRSSから見出し・概要を取得
2. `src/generate_script.py` … Gemini APIで「要約・言い換え」した独自台本を生成
3. `src/generate_audio.py` … 台本のナレーションを音声化（gTTS、無料）
4. `src/compose_video.py` … 音声＋字幕アニメーションを合成し、縦型mp4を出力
5. `src/main.py` … 上記1〜4を順番に実行するパイプライン
6. `.github/workflows/daily_video.yml` … 毎日自動実行するGitHub Actions設定

## セットアップ手順

### 1. Gemini APIキーを取得
https://aistudio.google.com/apikey でAPIキーを発行してください（無料枠あり）。

### 2. このリポジトリをGitHubにpush
```bash
git init
git add .
git commit -m "初期セットアップ"
git remote add origin <あなたのリポジトリURL>
git push -u origin main
```

### 3. GitHub SecretsにAPIキーを登録
リポジトリの `Settings > Secrets and variables > Actions > New repository secret` で

- Name: `GEMINI_API_KEY`
- Value: (取得したAPIキー)

を登録してください。

### 4. 動作確認（手動実行）
`Actions` タブ → `毎日ショート動画自動生成` → `Run workflow` で手動実行できます。
成功すると `Artifacts` に `short_video.mp4` がダウンロード可能な形で保存されます。

### 5. 自動実行の確認
`.github/workflows/daily_video.yml` の `cron: "0 21 * * *"` により
毎日 日本時間6:00 に自動実行されます（時刻を変えたい場合はcron式を編集してください）。

## ローカルでのテスト方法

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="あなたのAPIキー"
cd src
python main.py
```

`output/short_video.mp4` が生成されます。

## カスタマイズポイント

| やりたいこと | 編集するファイル |
|---|---|
| 収集するニュースサイトを変更 | `src/collect_trends.py` の `RSS_SOURCES` |
| 台本のトーン・文字数を変更 | `src/generate_script.py` の `SYSTEM_INSTRUCTION` |
| 音声をより自然なものに変更（有料） | `src/generate_audio.py` の `generate_audio()` をElevenLabs等のAPI呼び出しに差し替え |
| 映像を写真やAI生成映像に変更 | `src/compose_video.py` の `build_background_clip()` を差し替え |
| 実行時刻の変更 | `.github/workflows/daily_video.yml` の `cron` |

## 重要な注意事項（必ずお読みください）

- **著作権対策**：`generate_script.py` はGeminiに「元記事の表現をそのまま使わず要約・言い換えすること」を明示的に指示しています。ただし生成結果は必ず人の目で確認してから投稿することを推奨します。
- **SNSへの自動投稿は含まれていません**：本ツールは動画ファイルの生成までです。X/YouTube/TikTokへの自動投稿は各プラットフォームのAPI利用規約・自動投稿ポリシーの確認が別途必要なため、意図的に含めていません。生成された動画をArtifactsからダウンロードし、手動で確認・投稿することを推奨します。
- **無料枠の制限**：gTTSやGemini無料枠は利用量が多いと制限にかかる場合があります。継続運用する場合は各サービスの最新の利用規約・料金プランを確認してください。
- **音質について**：gTTSは無料な分、音質は簡易的です。より自然な音声が必要な場合は有料TTS（ElevenLabs等）への差し替えを検討してください。
