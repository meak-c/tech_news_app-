# tech_news_app v2 改善依頼

現在のv1は、公式ニュースを取得してHTML表示するところまで動いている。
次は、朝スマホで読むためのUI/UX改善を行う。

## 改善目的

単なる縦長のニュース一覧ではなく、毎朝スマホで見やすいニュースダッシュボードにする。

## 必須改善

### 1. 表示件数を制御する

初期表示では全ニュースを出さない。

初期表示ルール:
- 今日の新着ニュースは全件表示
- 今日の新着がない場合は、各プロダクトの最新3件を表示
- high importance は最新10件まで表示
- それ以外の古いニュースは「さらに表示」または月別アーカイブで見られるようにする

### 2. フィルタ機能を追加する

Vanilla JavaScriptで以下のフィルタを実装する。

- Product: All / ChatGPT / Claude / Claude Code / Databricks
- Month: All / YYYY-MM
- Importance: All / high / medium / low
- Search: タイトル・要約・取得元を対象に検索

フィルタ変更時、表示件数とニュース一覧を即時更新する。

### 3. JSONを生成する

Python側でHTMLだけでなく、以下も生成する。

public/news.json

JSONには最低限以下を含める。

- product
- title
- summary_ja
- published_at
- fetched_at
- source_name
- item_url
- importance
- is_new
- month

### 4. UIを刷新する

現在の素朴なHTMLを、モダンなテック系ダッシュボード風に変更する。

要件:
- スマホ優先
- 1カラム
- カードUI
- product別タグ
- importance別バッジ
- stickyなフィルタバー
- 軽いアニメーション
- 横スクロールなし
- 背景は落ち着いたグラデーション
- highは目立つが、警告色が強すぎない
- ダークすぎず朝に読みやすい

### 5. カードを折りたためるようにする

カードは初期状態で以下を表示する。

- product
- importance
- title
- published_at
- 要約の先頭
- 公式リンク

詳細部分には以下を入れる。

- 3点要約
- 取得元
- fetched_at
- 公式リンク

タップまたはクリックで詳細を開閉する。

### 6. 日本語要約を強制する

Gemini APIを使う場合、プロンプトを修正する。

ルール:
- 出力は必ず日本語
- 英語本文をそのまま貼らない
- 製品名、機能名、API名、CLIコマンドだけ英語のまま許可
- 形式は以下に固定する

・何が変わったか: ...
・影響: ...
・注意点: ...

LLM要約に失敗した場合、英語本文を長く表示しない。
代わりに以下のように表示する。

要約未生成。公式ページで確認してください。

### 7. テストを追加する

以下のテストを追加・更新する。

- news.json が生成される
- product / month / importance / is_new が含まれる
- 日本語要約失敗時に英語本文を長く出さない
- HTMLにフィルタUIが存在する
- app.js と styles.css が参照されている
- 初期表示で全ニュースがそのまま縦に出ない

## 技術制約

- React / Vue / Next.js は使わない
- Vanilla JSで実装
- GitHub Pagesでそのまま動く構成
- Python側の既存処理は壊さない
- GitHub Actionsは維持する
- `uv run pytest` が通ること
- `uv run python -m tech_news_app.main --no-llm` が通ること

## 受け入れ条件

1. public/index.html, public/styles.css, public/app.js, public/news.json が生成される
2. スマホで見やすいカードUIになっている
3. Product / Month / Importance / Search のフィルタが動く
4. 初期表示で過去ニュースが全部縦に出ない
5. Databricksなどの要約が英語本文そのままになりにくい
6. 要約失敗時は「要約未生成。公式ページで確認してください。」と表示される
7. GitHub PagesでJS/CSSが正しく読み込まれる
8. `uv run pytest` が成功する