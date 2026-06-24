from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import BaseLoader, Environment, select_autoescape

from .config import PRODUCTS
from .models import NewsItem, SourceError

JST = ZoneInfo("Asia/Tokyo")

INDEX_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Tech News Morning</title>
  <link rel="stylesheet" href="styles.css">
  <script defer src="app.js"></script>
</head>
<body>
  <main class="page-shell">
    <header class="hero">
      <p class="eyebrow">Official release notes only</p>
      <h1>Tech News Morning</h1>
      <p class="lead">ChatGPT / Claude / Claude Code / Databricks の更新を朝用に短く整理します。</p>
      <section class="status-panel" aria-label="更新状況">
        <p id="status-message">{{ status_message }}</p>
        <dl class="status-stats">
          <div><dt>新着</dt><dd id="new-count">{{ new_count }}</dd></div>
          <div><dt>総件数</dt><dd id="total-count">{{ total_count }}</dd></div>
        </dl>
      </section>
      {% if errors %}
      <section class="warning-panel" aria-label="取得エラー">
        <strong>一部のソース取得に失敗しました。</strong>
        <ul>
          {% for error in errors %}
          <li>{{ error.source_name }}: {{ error.message }}</li>
          {% endfor %}
        </ul>
      </section>
      {% endif %}
    </header>

    <section class="filters" aria-label="ニュースフィルタ">
      <label>
        <span>Product</span>
        <select id="product-filter">
          <option value="All">All</option>
          {% for product in products %}
          <option value="{{ product }}">{{ product }}</option>
          {% endfor %}
        </select>
      </label>
      <label>
        <span>Month</span>
        <select id="month-filter">
          <option value="All">All</option>
        </select>
      </label>
      <label>
        <span>Importance</span>
        <select id="importance-filter">
          <option value="All">All</option>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
        </select>
      </label>
      <label class="search-label">
        <span>Search</span>
        <input id="search-filter" type="search" placeholder="タイトル・要約・取得元">
      </label>
    </section>

    <section class="results-bar" aria-live="polite">
      <div>
        <span id="result-count">0</span>件を表示
        <span class="muted">/ <span id="matched-count">0</span>件一致</span>
      </div>
      <button id="show-more" type="button">さらに表示</button>
    </section>

    <section id="news-list" class="news-list" aria-label="ニュース一覧"></section>
    <p id="empty-message" class="empty-message" hidden>条件に一致するニュースはありません。</p>

    <footer class="footer">
      公式または公式に準ずる一次情報のみを掲載しています。
    </footer>
  </main>
</body>
</html>
"""

STYLES_CSS = """
:root {
  --bg-1: #eef6f6;
  --bg-2: #f8f3ea;
  --surface: rgba(255, 255, 255, 0.82);
  --surface-strong: #ffffff;
  --text: #21313a;
  --muted: #687782;
  --line: rgba(65, 89, 101, 0.16);
  --accent: #247480;
  --accent-soft: #dceff1;
  --high: #c65a35;
  --high-bg: #fff0e9;
  --medium: #8d6a1d;
  --medium-bg: #fff5d8;
  --low: #52606b;
  --low-bg: #edf1f3;
  --shadow: 0 16px 42px rgba(45, 67, 80, 0.12);
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
  font-size: 16px;
  line-height: 1.65;
  background:
    radial-gradient(circle at 18% 0%, rgba(109, 180, 185, 0.26), transparent 30rem),
    radial-gradient(circle at 90% 8%, rgba(238, 188, 114, 0.24), transparent 24rem),
    linear-gradient(145deg, var(--bg-1), var(--bg-2));
  min-height: 100vh;
}

a { color: var(--accent); text-underline-offset: 3px; }

button, select, input {
  font: inherit;
}

.page-shell {
  width: min(100% - 24px, 840px);
  margin: 0 auto;
  padding: 22px 0 52px;
}

.hero {
  padding: 22px 0 14px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 9vw, 4.2rem);
  line-height: 0.98;
  letter-spacing: -0.06em;
}

.lead {
  margin: 14px 0 18px;
  color: var(--muted);
}

.status-panel,
.warning-panel,
.filters,
.card {
  border: 1px solid var(--line);
  background: var(--surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(16px);
}

.status-panel {
  border-radius: 22px;
  padding: 16px;
}

#status-message {
  margin: 0;
  white-space: pre-line;
  font-weight: 650;
}

.status-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}

.status-stats div {
  border-radius: 16px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.62);
}

.status-stats dt {
  color: var(--muted);
  font-size: 0.78rem;
}

.status-stats dd {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
}

.warning-panel {
  margin-top: 14px;
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 248, 227, 0.9);
}

.filters {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  border-radius: 22px;
  padding: 12px;
}

.filters label {
  display: grid;
  gap: 4px;
}

.filters span {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.search-label {
  grid-column: 1 / -1;
}

select,
input[type="search"] {
  width: 100%;
  min-width: 0;
  border: 1px solid rgba(55, 80, 92, 0.18);
  border-radius: 14px;
  padding: 10px 11px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--text);
  outline: none;
}

select:focus,
input[type="search"]:focus {
  border-color: rgba(36, 116, 128, 0.72);
  box-shadow: 0 0 0 3px rgba(36, 116, 128, 0.13);
}

.results-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 18px 2px 12px;
  color: var(--text);
  font-weight: 700;
}

.muted { color: var(--muted); font-weight: 500; }

#show-more {
  border: 0;
  border-radius: 999px;
  padding: 9px 14px;
  color: #fff;
  background: linear-gradient(135deg, #247480, #315d7e);
  box-shadow: 0 8px 18px rgba(36, 116, 128, 0.22);
}

#show-more[hidden] { display: none; }

.news-list {
  display: grid;
  gap: 12px;
}

.card {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  background: var(--surface-strong);
  animation: card-in 180ms ease-out both;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-summary {
  width: 100%;
  display: grid;
  gap: 10px;
  border: 0;
  padding: 17px;
  color: inherit;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.card-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.tag,
.badge,
.new-label {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 0.72rem;
  font-weight: 850;
}

.tag {
  color: #1c5862;
  background: var(--accent-soft);
}

.badge-high { color: var(--high); background: var(--high-bg); }
.badge-medium { color: var(--medium); background: var(--medium-bg); }
.badge-low { color: var(--low); background: var(--low-bg); }

.new-label {
  color: #fff;
  background: linear-gradient(135deg, #c65a35, #d4894f);
}

.date {
  margin-left: auto;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 650;
}

.card h2 {
  margin: 0;
  font-size: 1.06rem;
  line-height: 1.42;
  letter-spacing: -0.01em;
}

.summary-preview {
  margin: 0;
  color: var(--muted);
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.official-link {
  font-size: 0.92rem;
  font-weight: 800;
}

.toggle-hint {
  color: var(--muted);
  font-size: 0.82rem;
}

.card-details {
  display: none;
  border-top: 1px solid var(--line);
  padding: 0 17px 17px;
}

.card.is-open .card-details {
  display: block;
}

.detail-summary {
  white-space: pre-line;
  margin: 14px 0;
}

.detail-meta {
  display: grid;
  gap: 3px;
  color: var(--muted);
  font-size: 0.82rem;
}

.empty-message,
.footer {
  color: var(--muted);
  text-align: center;
}

.empty-message {
  margin: 30px 0;
}

.footer {
  margin-top: 34px;
  font-size: 0.8rem;
}

@media (min-width: 700px) {
  .filters {
    grid-template-columns: 1fr 1fr 1fr 1.5fr;
  }

  .search-label {
    grid-column: auto;
  }
}
"""

APP_JS = """
const state = {
  items: [],
  expanded: false,
};

const els = {
  product: document.querySelector("#product-filter"),
  month: document.querySelector("#month-filter"),
  importance: document.querySelector("#importance-filter"),
  search: document.querySelector("#search-filter"),
  list: document.querySelector("#news-list"),
  resultCount: document.querySelector("#result-count"),
  matchedCount: document.querySelector("#matched-count"),
  totalCount: document.querySelector("#total-count"),
  showMore: document.querySelector("#show-more"),
  empty: document.querySelector("#empty-message"),
};

const collator = new Intl.Collator("ja-JP");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "公開日不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "公開日不明";
  return date.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function formatDateTime(value) {
  if (!value) return "不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "不明";
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summaryPreview(summary) {
  return String(summary || "要約未生成。公式ページで確認してください。")
    .replace(/・(何が変わったか|影響|注意点):/g, "")
    .replace(/\\s+/g, " ")
    .trim();
}

function populateMonths(items) {
  const months = [...new Set(items.map((item) => item.month).filter(Boolean))]
    .sort((a, b) => collator.compare(b, a));
  for (const month of months) {
    const option = document.createElement("option");
    option.value = month;
    option.textContent = month;
    els.month.append(option);
  }
}

function currentFilters() {
  return {
    product: els.product.value,
    month: els.month.value,
    importance: els.importance.value,
    search: els.search.value.trim().toLowerCase(),
  };
}

function filtersActive(filters) {
  return (
    filters.product !== "All" ||
    filters.month !== "All" ||
    filters.importance !== "All" ||
    filters.search !== ""
  );
}

function matches(item, filters) {
  if (filters.product !== "All" && item.product !== filters.product) return false;
  if (filters.month !== "All" && item.month !== filters.month) return false;
  if (filters.importance !== "All" && item.importance !== filters.importance) return false;
  if (filters.search) {
    const haystack = `${item.title} ${item.summary_ja} ${item.source_name}`.toLowerCase();
    if (!haystack.includes(filters.search)) return false;
  }
  return true;
}

function initialItems(items) {
  const newItems = items.filter((item) => item.is_new);
  const highItems = items.filter((item) => item.importance === "high").slice(0, 10);
  const selected = new Map();
  const add = (item) => selected.set(item.item_url, item);

  if (newItems.length) {
    newItems.forEach(add);
  } else {
    for (const product of ["ChatGPT", "Claude", "Claude Code", "Databricks"]) {
      items.filter((item) => item.product === product).slice(0, 3).forEach(add);
    }
  }
  highItems.forEach(add);
  return [...selected.values()];
}

function cardTemplate(item) {
  const title = escapeHtml(item.title);
  const summary = escapeHtml(item.summary_ja || "要約未生成。公式ページで確認してください。");
  const preview = escapeHtml(summaryPreview(item.summary_ja));
  const product = escapeHtml(item.product);
  const source = escapeHtml(item.source_name);
  const importance = escapeHtml(item.importance);
  const url = escapeHtml(item.item_url);
  return `
    <article class="card" data-product="${product}" data-month="${escapeHtml(item.month)}"
      data-importance="${importance}">
      <div class="card-summary" role="button" tabindex="0" aria-expanded="false">
        <span class="card-top">
          <span class="tag">${product}</span>
          <span class="badge badge-${importance}">${importance}</span>
          ${item.is_new ? '<span class="new-label">NEW</span>' : ""}
          <span class="date">${formatDate(item.published_at)}</span>
        </span>
        <h2>${title}</h2>
        <p class="summary-preview">${preview}</p>
        <span class="card-actions">
          <a class="official-link" href="${url}" rel="noopener noreferrer">公式リンク</a>
          <span class="toggle-hint">詳細を開く</span>
        </span>
      </div>
      <div class="card-details">
        <p class="detail-summary">${summary}</p>
        <div class="detail-meta">
          <span>取得元: ${source}</span>
          <span>取得日時: ${formatDateTime(item.fetched_at)}</span>
          <a href="${url}" rel="noopener noreferrer">公式ページで確認する</a>
        </div>
      </div>
    </article>
  `;
}

function render() {
  const filters = currentFilters();
  const matched = state.items.filter((item) => matches(item, filters));
  let visible = matched;

  if (!state.expanded && !filtersActive(filters)) {
    visible = initialItems(matched);
  }

  els.list.innerHTML = visible.map(cardTemplate).join("");
  els.resultCount.textContent = visible.length;
  els.matchedCount.textContent = matched.length;
  els.empty.hidden = matched.length !== 0;
  els.showMore.hidden =
    state.expanded || filtersActive(filters) || visible.length >= matched.length;

  for (const button of els.list.querySelectorAll(".card-summary")) {
    const toggle = (event) => {
      if (event.target.closest("a")) return;
      const card = button.closest(".card");
      const open = !card.classList.contains("is-open");
      card.classList.toggle("is-open", open);
      button.setAttribute("aria-expanded", String(open));
      card.querySelector(".toggle-hint").textContent = open ? "閉じる" : "詳細を開く";
    };
    button.addEventListener("click", toggle);
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggle(event);
      }
    });
  }
}

function onFilterChange() {
  state.expanded = false;
  render();
}

async function boot() {
  const response = await fetch("news.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`news.json load failed: ${response.status}`);
  const payload = await response.json();
  state.items = payload.items || [];
  els.totalCount.textContent = state.items.length;
  populateMonths(state.items);
  render();
}

for (const control of [els.product, els.month, els.importance, els.search]) {
  control.addEventListener("input", onFilterChange);
}

els.showMore.addEventListener("click", () => {
  state.expanded = true;
  render();
});

boot().catch((error) => {
  console.error(error);
  els.empty.hidden = false;
  els.empty.textContent = "ニュースデータの読み込みに失敗しました。";
});
"""


def _date_ja(value: datetime | None) -> str:
    if value is None:
        return "不明"
    return value.astimezone(JST).strftime("%Y/%m/%d")


def _month(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.astimezone(JST).strftime("%Y-%m")


def _status_message(run_at: datetime, new_count: int) -> str:
    run_jst = run_at.astimezone(JST)
    updated = run_jst.strftime("%Y/%m/%d %H:%M JST 更新")
    if new_count:
        return f"{updated}\n本日の新着ニュースがあります。"
    return (
        f"{updated}\n本日の新ニュースはありませんでした。\n"
        f"{run_jst:%Y/%m/%d} 時点で取得済みの最新ニュースを表示しています。"
    )


def render_html(
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> str:
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    return env.from_string(INDEX_TEMPLATE).render(
        products=PRODUCTS,
        errors=errors,
        status_message=_status_message(run_at, new_count),
        new_count=new_count,
        total_count=len(items),
    )


def render_news_json(items: list[NewsItem], run_at: datetime, new_count: int) -> str:
    payload = {
        "generated_at": run_at.astimezone(JST).isoformat(),
        "new_count": new_count,
        "items": [
            {
                "product": item.product,
                "title": item.title,
                "summary_ja": item.summary_ja or "要約未生成。公式ページで確認してください。",
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "fetched_at": item.fetched_at.isoformat(),
                "source_name": item.source_name,
                "item_url": item.item_url,
                "importance": item.importance.value,
                "is_new": item.is_new,
                "month": _month(item.published_at),
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_site(
    output_path: Path,
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> None:
    public_dir = output_path.parent
    write_text(output_path, render_html(items, errors, run_at, new_count))
    write_text(public_dir / "styles.css", STYLES_CSS.strip() + "\n")
    write_text(public_dir / "app.js", APP_JS.strip() + "\n")
    write_text(public_dir / "news.json", render_news_json(items, run_at, new_count) + "\n")
