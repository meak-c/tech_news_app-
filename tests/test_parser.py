from tech_news_app.config import SourceConfig
from tech_news_app.parser import (
    parse_claude_code_changelog,
    parse_claude_release_notes,
    parse_codex_changelog,
    parse_gemini_release_notes,
    parse_heading_document,
)


def source(product: str = "ChatGPT") -> SourceConfig:
    return SourceConfig(
        product=product,
        source_name="Official notes",
        url="https://example.com/releases",
    )


def test_heading_document_uses_date_heading_and_h2_items() -> None:
    html = """
    <article>
      <h1>June 23, 2026</h1>
      <h2 id="release">New feature</h2>
      <p>The feature is generally available.</p>
      <h3>Details</h3>
      <p>More detail.</p>
    </article>
    """
    items = parse_heading_document(html, source())
    assert len(items) == 1
    assert items[0].published_at.date().isoformat() == "2026-06-23"
    assert "More detail" in items[0].raw_text


def test_claude_release_notes_uses_date_sections() -> None:
    html = """
    <article>
      <div><h2>June 2026</h2></div>
      <div><h3 id="june-23">June 23, 2026</h3></div>
      <div><p>Claude added a new feature. It is available now.</p></div>
      <div><h3>June 20, 2026</h3></div>
    </article>
    """
    items = parse_claude_release_notes(html, source("Claude"))
    assert len(items) == 1
    assert items[0].title == "Claude added a new feature."


def test_claude_code_changelog_uses_update_blocks() -> None:
    html = """
    <div class="update-container" id="2-1-1">
      <div data-component-part="update-label">2.1.1</div>
      <div data-component-part="update-description">June 23, 2026</div>
      <div class="prose"><p>Fixed a CLI issue.</p></div>
    </div>
    """
    items = parse_claude_code_changelog(html, source("Claude Code"))
    assert len(items) == 1
    assert items[0].title == "v2.1.1"
    assert items[0].item_url.endswith("#2-1-1")


def test_gemini_release_notes_uses_h2_date_and_h3_items() -> None:
    html = """
    <article>
      <h1>リリースノート</h1>
      <h2>2026.07.21</h2>
      <h3>3.6 Flash: アップグレード版モデル</h3>
      <ul><li>更新内容: 新しいモデルが利用可能になりました。</li></ul>
      <h2>2026.06.30</h2>
      <h3>Gemini Spark is your 24/7 personal AI agent.</h3>
      <ul><li>更新内容: 新しいエージェント機能です。</li></ul>
    </article>
    """
    items = parse_gemini_release_notes(html, source("Gemini"))
    assert len(items) == 2
    assert items[0].title == "3.6 Flash: アップグレード版モデル"
    assert items[0].published_at.date().isoformat() == "2026-07-21"
    assert "新しいモデル" in items[0].raw_text
    assert items[1].published_at.date().isoformat() == "2026-06-30"


def test_codex_changelog_uses_time_and_prose_content() -> None:
    html = """
    <ul>
      <li id="github-release-1" data-products="codex">
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center gap-2"><time>2026-07-21</time></div>
          <h3><span>Codex CLI<span> 0.145.0</span></span></h3>
        </div>
        <article class="prose-content"><p>Added a new experimental feature.</p></article>
      </li>
    </ul>
    """
    items = parse_codex_changelog(html, source("Codex"))
    assert len(items) == 1
    assert items[0].title == "Codex CLI 0.145.0"
    assert items[0].published_at.date().isoformat() == "2026-07-21"
    assert items[0].item_url.endswith("#github-release-1")
    assert "experimental feature" in items[0].raw_text
