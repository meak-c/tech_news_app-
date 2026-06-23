from tech_news_app.config import SourceConfig
from tech_news_app.parser import (
    parse_claude_code_changelog,
    parse_claude_release_notes,
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
