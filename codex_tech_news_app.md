# Codex CLI 実装依頼: tech_news_app

## 目的

`apps/tech_news_app/` 配下に、個人用の技術ニュース朝刊アプリを作成してください。

このアプリは、公式ソース限定で以下のプロダクトの更新情報を毎日取得し、過去ニュースを蓄積し、日本語で要約したHTMLを生成します。

- ChatGPT
- Claude
- Claude Code
- Databricks

朝の電車でスマホから確認する用途を想定します。  
PCを起動していなくても閲覧できるように、GitHub Actions + GitHub Pages で運用できる構成にしてください。

---

## プロジェクト配置

このアプリは、リポジトリ内の以下のディレクトリをプロジェクトルートとして作成します。

```text
apps/tech_news_app/
```

既存リポジトリのルート直下に `apps/` がない場合は作成してください。

---

## 最重要要件

### 1. 公式ソース限定

ニュース取得元は、公式または公式に準ずる一次情報に限定してください。  
一般ニュースサイト、個人ブログ、SNS、Qiita、Zenn、Redditなどは対象外です。

初期版では以下の公式ソースを対象にしてください。

| product | source_name | url | 備考 |
|---|---|---|---|
| ChatGPT | ChatGPT Release Notes | https://help.openai.com/en/articles/6825453-chatgpt-release-notes | OpenAI公式Help |
| Claude | Claude Release Notes | https://support.claude.com/en/articles/12138966-release-notes | Anthropic公式Help |
| Claude Code | Claude Code Changelog | https://code.claude.com/docs/en/changelog | Anthropic公式Docs |
| Claude Code | Claude Code GitHub Releases | https://github.com/anthropics/claude-code/releases | Anthropic公式GitHub |
| Databricks | Databricks Release Notes | https://docs.databricks.com/aws/en/release-notes/ | Databricks公式Docs |

Claude Code は changelog と GitHub Releases の内容が重複する可能性があります。  
初期版では両方を取得対象にして構いませんが、同一URL・同一タイトル・近い公開日による簡易重複排除を入れてください。

---

### 2. 毎朝3時に自動実行できること

GitHub Actions で毎日 JST 03:00 頃に実行できるようにしてください。

GitHub Actions の cron は UTC 基準なので、日本時間 03:00 は前日 18:00 UTC です。

```yaml
cron: "0 18 * * *"
```

手動実行もできるように `workflow_dispatch` を入れてください。

---

### 3. 過去ニュースを蓄積すること

更新がない日でも、過去に取得済みの最新ニュースを表示したいです。

そのため、取得したニュースは保存してください。

初期版では SQLite を推奨します。

保存先の例:

```text
apps/tech_news_app/data/news.sqlite
```

ただし、GitHub Actions + GitHub Pages 運用で扱いやすいなら JSON でも構いません。  
判断に迷う場合は SQLite を採用してください。

最低限、以下の情報を保存してください。

| column | description |
|---|---|
| id | 主キー |
| product | ChatGPT / Claude / Claude Code / Databricks |
| source_name | 取得元名 |
| source_url | 取得元URL |
| item_url | ニュース個別URL。個別URLがない場合は source_url |
| title | ニュースタイトル |
| published_at | 公開日。取得できない場合はNULL |
| fetched_at | 取得日時 |
| first_seen_at | 初回検知日時 |
| last_seen_at | 最終確認日時 |
| content_hash | 重複判定用ハッシュ |
| summary_ja | 日本語要約 |
| raw_text | 取得した本文または抜粋 |
| importance | high / medium / low |
| created_at | レコード作成日時 |
| updated_at | レコード更新日時 |

---

### 4. 新規ニュースがない日もHTMLを生成すること

毎回HTMLは必ず生成してください。

新規ニュースがある場合:

```text
2026/06/23 03:00 JST 更新

本日の新着ニュースがあります。
```

新規ニュースがない場合:

```text
2026/06/23 03:00 JST 更新

本日の新ニュースはありませんでした。
2026/06/23 時点で取得済みの最新ニュースを表示しています。
```

このメッセージはHTMLの上部に表示してください。

---

### 5. スマホで見やすいHTMLを生成すること

生成先は以下を想定してください。

```text
apps/tech_news_app/public/index.html
```

GitHub Pages で配信しやすいように、CSSはHTML内に直接書いても構いません。  
初期版ではビルドツールは不要です。

スマホ表示を最優先にしてください。

必要な表示要素:

- 更新日時
- 今日の新規ニュース件数
- 新規ニュースがない場合の案内メッセージ
- product別のカード表示
- 重要度ラベル
- 公開日
- タイトル
- 日本語要約
- 公式リンク
- 取得元名

デザイン要件:

- 1カラム
- 横スクロールなし
- 文字サイズはスマホで読みやすく
- productごとに見出しを分ける
- `high` は目立つ表示
- `medium` と `low` も区別できる表示
- ダークすぎない落ち着いた色
- 朝の電車で読める程度に情報密度を抑える

---

## 要約について

### 初期版の方針

Gemini API を使って日本語要約してください。  
APIキーは環境変数から取得してください。

```bash
GEMINI_API_KEY
```

APIキーが設定されていない場合は、アプリを落とさず、本文抜粋ベースの簡易要約を生成してください。

つまり、以下のどちらでも動くようにしてください。

1. `GEMINI_API_KEY` あり: Gemini APIで日本語要約
2. `GEMINI_API_KEY` なし: 取得本文の先頭から簡易要約を作成

### 要約のルール

日本語要約では以下を重視してください。

- 何が変わったか
- 誰に影響があるか
- すでに利用可能か、Previewか、段階的ロールアウトか
- CLIやAPIの破壊的変更があるか
- 料金・プラン・権限・セキュリティに関わる変更があるか

出力は短くしてください。

推奨フォーマット:

```text
・何が変わったか: ...
・影響: ...
・注意点: ...
```

---

## 重要度判定

初期版ではルールベースで構いません。

### high

以下を含むもの:

- new model
- launch
- GA
- generally available
- pricing
- security
- breaking change
- deprecation
- Claude Code / CLI の大きな変更
- Databricks Runtime の重要更新
- 権限・認証・管理機能に関わる変更

### medium

以下を含むもの:

- feature
- improvement
- preview
- beta
- connector
- integration
- UI改善
- 管理画面改善

### low

以下を含むもの:

- bug fix
- minor
- documentation
- small improvement

判定に迷う場合は `medium` にしてください。

---

## 重複排除

最低限、以下で重複を避けてください。

1. `item_url` が同じなら同一ニュース
2. `title + product + published_at` が同じなら同一ニュース
3. `content_hash` が同じなら同一ニュース

Claude Code は公式DocsとGitHub Releasesで内容が被りやすいため、完全でなくてよいので簡易重複排除を入れてください。

初期版では高度な類似度判定は不要です。

---

## ディレクトリ構成

以下の構成を作成してください。

```text
apps/tech_news_app/
├── README.md
├── pyproject.toml
├── .python-version
├── src/
│   └── tech_news_app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── fetchers.py
│       ├── parser.py
│       ├── storage.py
│       ├── summarizer.py
│       ├── renderer.py
│       └── models.py
├── data/
│   └── .gitkeep
├── public/
│   └── .gitkeep
└── tests/
    ├── test_storage.py
    ├── test_importance.py
    └── test_renderer.py
```

GitHub Actions workflow はリポジトリルート側に置く必要があります。

```text
.github/workflows/tech_news_app.yml
```

このworkflowから `apps/tech_news_app/` に移動して実行してください。

---

## Python環境

Pythonの環境管理は `uv` を使ってください。

Pythonバージョンは以下を想定します。

```text
3.12
```

`.python-version`:

```text
3.12
```

`pyproject.toml` には最低限以下を含めてください。

- requests
- beautifulsoup4
- feedparser
- python-dateutil
- jinja2
- pydantic
- pytest
- ruff

Gemini API用ライブラリは、公式SDKを使うか、HTTPリクエストで実装してください。  
依存を増やしすぎない方針でお願いします。

---

## CLI仕様

以下のコマンドで実行できるようにしてください。

```bash
cd apps/tech_news_app
uv run python -m tech_news_app.main
```

オプションも用意してください。

```bash
uv run python -m tech_news_app.main --no-llm
uv run python -m tech_news_app.main --dry-run
uv run python -m tech_news_app.main --output public/index.html
```

### オプション説明

| option | description |
|---|---|
| `--no-llm` | Gemini APIを使わず、本文抜粋で要約する |
| `--dry-run` | DB更新やHTML出力をせず、取得結果だけ表示する |
| `--output` | HTML出力先を指定する |

---

## GitHub Actions要件

`.github/workflows/tech_news_app.yml` を作成してください。

要件:

- JST 03:00相当で毎日実行
- 手動実行可能
- `uv` をセットアップ
- `apps/tech_news_app/` 配下で実行
- 生成された `public/index.html` をPagesにデプロイできること
- `GEMINI_API_KEY` はGitHub Secretsから読むこと
- APIキーがない場合でも失敗させないこと

GitHub Pagesへのデプロイ方法は、GitHub公式の `actions/upload-pages-artifact` と `actions/deploy-pages` を使う構成を優先してください。

---

## エラーハンドリング

1つのソース取得に失敗しても、全体を止めないでください。

例:

- ChatGPTの取得に失敗
- Claudeは成功
- Claude Codeは成功
- Databricksは成功

この場合、HTMLは生成してください。  
上部に警告を表示してください。

```text
一部のソース取得に失敗しました。
- ChatGPT Release Notes: HTTP 500
```

DBには実行ログも保存してください。

最低限、以下を保存してください。

| column | description |
|---|---|
| id | 主キー |
| run_at | 実行日時 |
| status | success / partial_success / failed |
| new_item_count | 新規ニュース件数 |
| error_message | エラー概要 |
| created_at | 作成日時 |

---

## テスト要件

最低限、以下のテストを作成してください。

### test_storage.py

- 新規ニュースをinsertできる
- 同じURLのニュースを重複insertしない
- 新規ニュースがない場合でも最新ニュースを取得できる

### test_importance.py

- `breaking change` を含むタイトルは high
- `bug fix` を含むタイトルは low
- 判断不能なタイトルは medium

### test_renderer.py

- 新規ニュースがない場合、以下の文言がHTMLに含まれる

```text
本日の新ニュースはありませんでした。
```

- product別の見出しが出る
- 公式リンクが出る

---

## READMEに書くこと

`apps/tech_news_app/README.md` に以下を書いてください。

- このアプリの目的
- 対象プロダクト
- 公式ソース一覧
- ローカル実行方法
- `uv` セットアップ方法
- `GEMINI_API_KEY` の設定方法
- GitHub Actionsの実行方法
- GitHub Pagesで見る方法
- 更新なしの日の挙動
- トラブルシュート

---

## 実装方針

初期版では、完璧なスクレイピング精度より、壊れにくく運用できることを優先してください。

優先順位:

1. 毎日動く
2. 過去ニュースが蓄積される
3. 新規なしの日も意味のあるHTMLが出る
4. スマホで読みやすい
5. 公式ソースへのリンクが必ずある
6. LLM要約がなくても最低限読める
7. テストで最低限の品質が担保される

高度な機能は初期版では不要です。

不要なもの:

- 認証付きWebアプリ
- React / Vue / Next.js
- DBサーバー
- Docker
- Slack通知
- Gmail通知
- 既読管理
- 高度な類似度ベースの重複排除
- 一般ニュースサイト取得
- SNS取得

---

## 受け入れ条件

以下を満たしたら完了です。

1. `apps/tech_news_app/` 配下にアプリが作成されている
2. `uv run python -m tech_news_app.main --no-llm` が成功する
3. `apps/tech_news_app/public/index.html` が生成される
4. `GEMINI_API_KEY` がなくても動く
5. SQLite DBにニュースと実行ログが保存される
6. 新規ニュースがない2回目以降の実行で、HTMLに以下が表示される

```text
本日の新ニュースはありませんでした。
```

7. ChatGPT / Claude / Claude Code / Databricks のセクションがHTMLに表示される
8. 公式リンクがHTMLに表示される
9. `uv run pytest` が成功する
10. `.github/workflows/tech_news_app.yml` が作成されている

---

## 実装時の注意

- 取得失敗時に即終了しないでください。
- HTMLには必ず公式リンクを出してください。
- タイムゾーンは JST を基準にしてください。
- UTC/JSTの変換ミスに注意してください。
- 公式ページのHTML構造が変わっても、完全に落ちないようにしてください。
- parserはソースごとに分けても構いません。
- 最初から完璧な本文抽出を狙わなくてよいです。
- ただし、タイトル・日付・URL・取得元はできるだけ保存してください。
- LLM要約が失敗した場合も、簡易要約にフォールバックしてください。

---

## 最初にやること

まず、`apps/tech_news_app/` の雛形を作成してください。  
その後、以下の順に実装してください。

1. models
2. storage
3. importance判定
4. fetchers
5. summarizer
6. renderer
7. main CLI
8. tests
9. GitHub Actions
10. README

完了後、以下のコマンドを実行して結果を確認してください。

```bash
cd apps/tech_news_app
uv run python -m tech_news_app.main --no-llm
uv run pytest
```

---

## 実現可能性の検証結果

検証日: 2026-06-23

### 結論

初期版の要件は実現可能です。  
公式ページの取得、SQLiteへの蓄積、Gemini APIによる日本語要約、静的HTML生成、GitHub Actionsでの定期実行、GitHub Pagesへの公開は、いずれもPythonとGitHubの標準機能で構成できます。

無料での運用も可能です。ただし、以下を前提とします。

- GitHub PagesをGitHub Freeで使う場合は、原則としてpublicリポジトリで運用する
- GitHub Actionsは標準のGitHub-hosted runnerを使用する
- Gemini APIはFree Tier対象モデルを使用し、Google Cloudの有料Tierへ移行しない
- Gemini APIのレート制限時や障害時は、本文抜粋による簡易要約へフォールバックする
- このアプリに不要なGoogle Search Grounding、画像生成、動画生成などは使用しない

### Gemini APIの無料運用方針

初期モデルは、安定版かつFree Tierでテキストの入出力が無料の以下を推奨します。

```text
gemini-2.5-flash-lite
```

モデル名は将来変更できるよう、コードへ固定せず、次の環境変数で上書き可能にしてください。

```bash
GEMINI_MODEL=gemini-2.5-flash-lite
```

Free Tierのレート制限値はモデルやプロジェクト状態によって変わるため、固定値を前提にしないでください。429応答時は短い待機を伴う少数回の再試行を行い、それでも失敗した場合は簡易要約へ切り替えてHTML生成を継続してください。

Free Tierでは、送信内容がGoogleの製品改善に利用される場合があります。そのため、Gemini APIへ送る内容は公開済みの公式リリースノート本文または抜粋だけに限定し、APIキー、ログ、個人情報、リポジトリ内の非公開情報はプロンプトへ含めないでください。

### ニュース取得の実現性と注意点

指定された5つの公式ソースは、検証日時点でHTTP経由で参照でき、更新日・見出し・本文を取得できるため実装可能です。

ただし、公式サイト側のHTML構造変更は避けられません。ソースごとにパーサーを分離し、1つのパーサーが壊れても他の取得とHTML生成を継続できる構造にしてください。

- ChatGPT、Claude、Claude Code Docsは、日付見出しと更新見出しを基準に解析する
- Claude Code GitHub Releasesは、可能ならHTMLスクレイピングよりGitHub ReleasesのAtomフィードまたはGitHub APIを優先する
- Databricks Release Notesは一覧ページ自体に全文がないため、公式ドメイン内のリリースノート詳細ページをたどる必要がある
- 取得本文のサイズを制限し、新規または要約未作成のニュースだけをGemini APIへ送信して無料枠を節約する

### SQLite永続化に関する必須修正

GitHub Actionsのrunnerは実行ごとに破棄され、GitHub Pagesへアップロードしたartifactもアプリの永続DBにはなりません。単に`data/news.sqlite`を更新してPagesへデプロイするだけでは、次回実行時に過去ニュースを読み戻せません。

初期版では、次の方針を採用してください。

1. workflow開始時にリポジトリをcheckoutする
2. `data/news.sqlite`を読み書きする
3. 実行後に`data/news.sqlite`を同じリポジトリへcommitしてpushする
4. HTMLは`public/`をPages artifactとしてデプロイする
5. workflowへ`contents: write`、`pages: write`、`id-token: write`を必要最小限で設定する
6. 同時実行によるDB競合を避けるため、workflowに`concurrency`を設定する

SQLiteはバイナリファイルのため、毎日のcommitでリポジトリサイズが増加します。個人用の初期版では許容できますが、長期運用では古い実行ログの削除、`VACUUM`、DBバックアップ、またはJSON/外部ストレージへの移行を検討してください。

GitHub Actionsのcronは指定時刻ちょうどの実行を保証せず、毎時0分付近は遅延する可能性があります。要件が「JST 03:00頃」であれば、遅延を減らすため次のように数分ずらすことも許容します。

```yaml
cron: "7 18 * * *"
```

### APIキーの保管場所

APIキーの実値は、このMarkdown、ソースコード、workflow YAML、`.env.example`、生成HTML、SQLite、ログへ絶対に記述しないでください。

GitHub Actionsでは、リポジトリの次の場所へRepository Secretとして保存します。

```text
GitHub repository
  → Settings
  → Secrets and variables
  → Actions
  → New repository secret
```

Secret名:

```text
GEMINI_API_KEY
```

workflowではSecretを環境変数へ渡します。Secretが未登録の場合は空文字として扱われるため、アプリ側で未設定を検出して簡易要約へフォールバックしてください。

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  GEMINI_MODEL: gemini-2.5-flash-lite
```

ローカル実行では、シェルの環境変数として設定します。

```bash
export GEMINI_API_KEY="実際のAPIキー"
export GEMINI_MODEL="gemini-2.5-flash-lite"
uv run python -m tech_news_app.main
```

ローカルで`.env`を使う場合は必ず`.gitignore`へ追加し、実値をcommitしないでください。リポジトリにはキー名だけを書いた`.env.example`を置けます。

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
```

2026-06-19以降、Gemini APIでは無制限のstandard API keyを保護する必要があります。Google AI Studioで新しいauth keyを作成するか、既存キーを「Gemini API only」に制限してください。キー漏えい時は直ちに新しいキーへ交換し、旧キーを無効化してください。

### 検証に使用した公式資料

- Gemini API Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API Rate Limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini API Key Security: https://ai.google.dev/gemini-api/docs/api-key
- GitHub Actions Secrets: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- GitHub Actions Schedule: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- GitHub Actions Billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub Pages Custom Workflows: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
