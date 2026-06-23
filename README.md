# Tech News Morning

ChatGPT、Claude、Claude Code、Databricksの公式更新情報だけを毎日収集し、日本語の短い朝刊HTMLを生成する個人用アプリです。GitHub ActionsでJST 03:07頃に実行し、GitHub Pagesへ公開します。

## 対象ソース

| 製品 | 公式ソース |
|---|---|
| ChatGPT | [ChatGPT Release Notes](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) |
| Claude | [Claude Release Notes](https://support.claude.com/en/articles/12138966-release-notes) |
| Claude Code | [Claude Code Changelog](https://code.claude.com/docs/en/changelog) |
| Claude Code | [GitHub Releases](https://github.com/anthropics/claude-code/releases) |
| Databricks | [Databricks Release Notes](https://docs.databricks.com/aws/en/release-notes/) |

一般ニュースサイト、ブログ、SNSは取得しません。

## ローカル実行

前提はPython 3.12と[`uv`](https://docs.astral.sh/uv/)です。

```bash
uv sync --all-extras
uv run python -m tech_news_app.main --no-llm
```

生成物:

- SQLite: `data/news.sqlite`
- HTML: `public/index.html`

主なオプション:

```bash
uv run python -m tech_news_app.main --no-llm
uv run python -m tech_news_app.main --dry-run
uv run python -m tech_news_app.main --output public/preview.html
```

`--dry-run`はニュース取得結果をJSONで表示し、DBとHTMLを変更しません。

## Gemini API

Geminiを使用しない場合でも動作します。APIキーがない場合やAPI呼び出しに失敗した場合は、取得本文の抜粋を表示します。

推奨モデル:

```text
gemini-2.5-flash-lite
```

ローカルでは環境変数に設定します。

```bash
export GEMINI_API_KEY="実際のAPIキー"
export GEMINI_MODEL="gemini-2.5-flash-lite"
export GEMINI_MIN_INTERVAL_SECONDS="4.1"
uv run python -m tech_news_app.main
```

`.env`を使う場合は手動で読み込んでください。このアプリは秘密情報の意図しない読み込みを避けるため、`.env`を自動ロードしません。

```bash
set -a
source .env
set +a
uv run python -m tech_news_app.main
```

APIキーの実値をソースコード、`.env.example`、HTML、DBへ保存しないでください。GitHubではRepository Secret `GEMINI_API_KEY`へ保存します。

Free Tierへ送る内容は公開済みの公式リリースノートに限定しています。料金とレート制限は変更されるため、運用前に[Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)を確認してください。

`GEMINI_MIN_INTERVAL_SECONDS`は無料枠のRPM制限を避けるための呼び出し間隔です。初回は既存ニュースを順番に要約するため数分かかる場合があります。

## テストと静的チェック

```bash
uv run pytest
uv run ruff check .
```

## GitHub Actions

workflowは`.github/workflows/tech_news_app.yml`です。

- 毎日18:07 UTC（JST 03:07頃）に実行
- Actions画面から手動実行可能
- テスト後にニュースを取得
- `data/news.sqlite`をリポジトリへcommitして次回へ引き継ぐ
- `public/`をGitHub Pagesへデプロイ
- 1つの取得元が失敗しても、残りのニュースからHTMLを生成

SQLiteをpushするため、workflowには`contents: write`が必要です。branch protectionでbotの直接pushを禁止している場合、この永続化処理は失敗します。

## GitHub Pages

リポジトリのSettings → Pages → Build and deployment → Sourceで`GitHub Actions`を選択します。workflowが成功すると、`github-pages` environmentのURLから閲覧できます。

GitHub FreeでPagesを無料利用する場合はpublicリポジトリが基本です。privateリポジトリで利用できるかは契約プランを確認してください。

## 更新がない日の挙動

毎回HTMLを生成します。新規ニュースがなければ、次の案内とDB内の最新ニュースを表示します。

```text
本日の新ニュースはありませんでした。
```

## データ永続化

GitHub-hosted runnerは実行後に破棄されるため、Pages artifactだけではDBを保存できません。このアプリはworkflowから`data/news.sqlite`をリポジトリへcommitします。

SQLiteはバイナリなので履歴サイズが増えます。長期運用では定期的な`VACUUM`、実行ログの整理、または外部ストレージへの移行を検討してください。

## トラブルシュート

### APIキーがない

正常動作です。本文抜粋による簡易要約になります。

### HTTP 403、429

取得先またはGemini APIの制限です。HTMLには取得エラーが表示されます。Geminiの失敗時は簡易要約へ切り替わります。

### DBをpushできない

Repository Settings → Actions → General → Workflow permissionsで書き込み権限を許可し、branch protectionも確認してください。

### Pages deployが失敗する

Settings → PagesのSourceが`GitHub Actions`になっているか、workflowに`pages: write`と`id-token: write`があるか確認してください。

### cronが時刻どおりに始まらない

GitHub Actionsのscheduleは遅延する場合があります。03:07は目安です。必要ならActions画面から手動実行してください。
