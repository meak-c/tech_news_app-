# tech_news_app アーキテクチャ

このドキュメントは、`tech_news_app` がどのサービス・ファイル・処理を使って毎朝のニュースページを生成するかを説明します。

## 全体構成

```mermaid
flowchart TD
    Schedule[GitHub Actions<br>schedule / workflow_dispatch]
    Runner[GitHub-hosted runner<br>Ubuntu]
    App[Python app<br>tech_news_app.main]
    Sources[Official sources<br>OpenAI / Anthropic / Google / GitHub Releases]
    Gemini[Gemini API<br>Japanese summary]
    SQLite[(data/news.sqlite<br>news + run_logs)]
    Public[web/public/news.json<br>+ web/ React build -> web/dist]
    Repo[(GitHub repository<br>source + SQLite history)]
    Artifact[Pages artifact]
    Pages[GitHub Pages]
    Phone[Smartphone browser]

    Schedule --> Runner
    Runner --> App
    App --> Sources
    App --> Gemini
    App <--> SQLite
    App --> Public
    SQLite --> Repo
    Public --> Artifact
    Artifact --> Pages
    Pages --> Phone
```

## 処理フロー

### 1. GitHub Actionsが起動する

`.github/workflows/tech_news_app.yml` が起点です。

起動方法は2つあります。

- 毎日JST 03:07頃の定期実行
- GitHub Actions画面からの手動実行

GitHub ActionsのcronはUTC基準なので、workflowでは `7 18 * * *` を指定しています。これはJSTでは翌日03:07です。03:00ちょうどではなく03:07にしているのは、GitHub Actionsの毎時0分付近の混雑を避けるためです。

### 2. Runner上でPython環境を作る

GitHub-hosted runner上で以下を実行します。

1. リポジトリをcheckout
2. Python 3.12をセットアップ
3. `uv`をセットアップ
4. `uv sync --project collector --locked --all-extras` で依存関係を復元
5. `uv run --project collector pytest collector` でテストを実行

この段階でテストが失敗すると、ニュース取得やPagesデプロイには進みません。

### 3. 公式ソースからニュースを取得する

Pythonアプリは `collector/src/tech_news_app/fetchers.py` と `parser.py` を使って、公式または公式に準ずる一次情報だけを取得します。

対象は以下です。

- OpenAI Help: ChatGPT Release Notes
- Anthropic Support: Claude Release Notes
- Anthropic Docs: Claude Code Changelog
- GitHub Releases: `anthropics/claude-code`
- Google: Gemini Release Notes
- OpenAI: Codex Changelog

取得元ごとにHTML構造が違うため、パーサーはソース別に分けています。1つのソース取得に失敗しても、他のソースの取得とサイト生成は継続します。

### 4. Gemini APIで日本語要約する

`GEMINI_API_KEY` がGitHub ActionsのRepository Secretに設定されている場合、`collector/src/tech_news_app/summarizer.py` がGemini APIを呼び出して日本語要約を生成します。

使用モデルは環境変数で指定します。

```text
GEMINI_MODEL=gemini-3.5-flash-lite
```

無料枠のレート制限を避けるため、呼び出し間隔は以下で制御します。

```text
GEMINI_MIN_INTERVAL_SECONDS=4.1
```

Gemini APIキーが未設定、API呼び出し失敗、レート制限、その他エラーの場合でもアプリは止まりません。その場合は、英語本文を長く表示せず、以下の定型文にフォールバックします。

```text
要約未生成。公式ページで確認してください。
```

この定型文のまま保存された記事は、次回以降の実行で再要約します。取得範囲に含まれる記事は取得時に、取得範囲外の過去記事は新しい順に1回あたり最大50件まで再要約し、API失敗を検知した時点で打ち切ります。

### 5. SQLiteへニュースと実行ログを保存する

保存先は以下です。

```text
data/news.sqlite
```

SQLiteには主に2種類のデータを保存します。

- `news`: ニュース本文、要約、URL、公開日、重要度、重複判定用hashなど
- `run_logs`: 実行日時、成功/部分成功/失敗、新規件数、エラー概要など

重複判定は次の観点で行います。

- 同じ `item_url`
- 同じ `product + title + published_at`
- 同じ `content_hash`

GitHub-hosted runnerは実行ごとに破棄されるため、SQLiteをrunner内に置くだけでは次回へ引き継げません。そのため、workflowの最後で `data/news.sqlite` をGitHubリポジトリへcommitしてpushします。

### 6. news.jsonを出力し、Webサイトをビルドする

`collector/src/tech_news_app/exporter.py` がDBの全ニュースを `web/public/news.json` へ出力します。news.jsonには記事一覧のほか、生成日時、新着件数、プロダクト一覧、取得エラーを含めます。

画面は `web/`(Vite + React + TypeScript)です。`npm run build` で `web/public/news.json` を含む静的ファイルを `web/dist/` へ出力します。

- `src/App.tsx`: news.jsonの読み込み、フィルタ状態、初期表示(Highlights)と「さらに表示」の制御
- `src/components/`: ヘッダー、フィルタバー、ニュースカード
- `src/lib/news.ts`: 絞り込み、初期表示の選定、日付グループ化、3行要約の分解(vitestでテスト)

### 7. GitHub Pagesへデプロイする

workflowは `web/dist/` をPages artifactとしてアップロードし、`actions/deploy-pages` でGitHub Pagesへ配信します。

スマホからはGitHub PagesのURLへアクセスします。

```text
https://meak-c.github.io/tech_news_app-/
```

ブラウザは `index.html` とビルド済みのJS/CSSを読み込み、その後 `news.json` を取得してニュースダッシュボードを表示します。

## 主要コンポーネント

| コンポーネント | 役割 |
|---|---|
| GitHub Actions | 定期実行、テスト、ニュース生成、DB永続化、Pagesデプロイ |
| GitHub-hosted runner | Pythonアプリの実行とWebビルドを行う一時的なUbuntu環境 |
| uv | Python依存関係の解決と実行 |
| Python app (collector/) | 取得、解析、要約、保存、news.json出力 |
| Gemini API | 日本語要約生成 |
| SQLite | ニュース履歴と実行ログの保存 |
| GitHub repository | ソースコードとSQLiteの永続化 |
| GitHub Pages | スマホから閲覧する静的サイト配信 |
| React app (web/) | フィルタ、検索、カード開閉、初期表示制御 |

## データの流れ

```mermaid
sequenceDiagram
    participant GH as GitHub Actions
    participant App as Python app
    participant Src as Official sources
    participant DB as SQLite
    participant LLM as Gemini API
    participant Pub as web/
    participant Pages as GitHub Pages

    GH->>App: uv run --project collector python -m tech_news_app.main
    App->>Src: 公式リリースノート取得
    Src-->>App: HTML / Atom feed
    App->>DB: 既存ニュース照合
    App->>LLM: 新規・未要約ニュースを要約
    LLM-->>App: 日本語3点要約
    App->>DB: news / run_logs保存
    App->>Pub: web/public/news.json出力
    GH->>DB: data/news.sqliteをcommit & push
    GH->>Pub: npm run build
    GH->>Pages: web/dist/をdeploy
```

## 運用上の注意

- Gemini APIキーはGitHub Secretsの `GEMINI_API_KEY` に保存します。
- APIキーの実値はMarkdown、ソースコード、JSON、SQLite、ログへ書きません。
- Free Tier運用では、Geminiへ送る内容を公開済み公式リリースノートに限定します。
- GitHub Pages artifactだけではSQLiteは永続化されないため、DBをリポジトリへcommitします。
- SQLiteはバイナリファイルなので、長期運用では履歴サイズが増えます。
- 取得元サイトのHTML構造変更で一部パーサーが壊れる可能性があります。その場合も他ソースの取得とサイト生成は継続する設計です。
