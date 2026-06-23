from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import BaseLoader, Environment, select_autoescape

from .config import PRODUCTS
from .models import NewsItem, SourceError

JST = ZoneInfo("Asia/Tokyo")

TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Tech News Morning</title>
  <style>
    :root { --bg:#f5f7f8; --card:#fff; --text:#24313a; --muted:#64727c;
      --line:#dce3e7; --accent:#286c78; --high:#b42318; --medium:#9a6700; --low:#52606b; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;
      font-size:16px; line-height:1.65; }
    main { width:min(100% - 28px, 760px); margin:0 auto; padding:24px 0 48px; }
    header { margin-bottom:24px; }
    h1 { margin:0 0 8px; font-size:1.65rem; letter-spacing:.01em; }
    h2 { margin:32px 0 12px; font-size:1.3rem; border-bottom:2px solid var(--accent);
      padding-bottom:6px; }
    .status { background:#e8f2f3; border-left:4px solid var(--accent); padding:14px 16px;
      border-radius:8px; white-space:pre-line; }
    .meta { color:var(--muted); font-size:.9rem; margin-top:8px; }
    .warning { background:#fff4e5; border:1px solid #f1c27d; padding:12px 16px;
      border-radius:8px; margin-top:14px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
      padding:17px; margin:12px 0; box-shadow:0 2px 8px rgba(30,50,60,.04);
      overflow-wrap:anywhere; }
    .card h3 { font-size:1.08rem; line-height:1.45; margin:8px 0; }
    .badge { display:inline-block; color:#fff; border-radius:999px; padding:2px 9px;
      font-size:.75rem; font-weight:700; text-transform:uppercase; }
    .high { background:var(--high); } .medium { background:var(--medium); }
    .low { background:var(--low); }
    .new { color:var(--high); font-weight:700; font-size:.8rem; margin-left:7px; }
    .summary { white-space:pre-line; margin:12px 0; }
    .source { color:var(--muted); font-size:.84rem; }
    a { color:#176978; text-underline-offset:3px; }
    .empty { color:var(--muted); padding:10px 0; }
    footer { color:var(--muted); font-size:.8rem; margin-top:36px; }
    @media (max-width:420px) {
      main { width:min(100% - 20px, 760px); padding-top:18px; }
      .card { padding:15px; } h1 { font-size:1.45rem; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <h1>Tech News Morning</h1>
    <div class="status">{{ status_message }}</div>
    <div class="meta">本日の新規ニュース: {{ new_count }}件</div>
    {% if errors %}
    <div class="warning">
      <strong>一部のソース取得に失敗しました。</strong>
      <ul>
        {% for error in errors %}
        <li>{{ error.source_name }}: {{ error.message }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
  </header>
  {% for product in products %}
  <section>
    <h2>{{ product }}</h2>
    {% if grouped[product] %}
      {% for item in grouped[product] %}
      <article class="card">
        <span class="badge {{ item.importance.value }}">{{ item.importance.value }}</span>
        {% if item.is_new %}<span class="new">NEW</span>{% endif %}
        <h3>{{ item.title }}</h3>
        <div class="meta">公開日: {{ item.published_at|date_ja }}</div>
        <div class="summary">{{ item.summary_ja }}</div>
        <a href="{{ item.item_url }}" rel="noopener noreferrer">公式情報を開く</a>
        <div class="source">取得元: {{ item.source_name }}</div>
      </article>
      {% endfor %}
    {% else %}
      <div class="empty">取得済みのニュースはありません。</div>
    {% endif %}
  </section>
  {% endfor %}
  <footer>公式または公式に準ずる一次情報のみを掲載しています。</footer>
</main>
</body>
</html>
"""


def _date_ja(value: datetime | None) -> str:
    if value is None:
        return "不明"
    return value.astimezone(JST).strftime("%Y/%m/%d")


def render_html(
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> str:
    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        grouped[item.product].append(item)
    run_jst = run_at.astimezone(JST)
    updated = run_jst.strftime("%Y/%m/%d %H:%M JST 更新")
    if new_count:
        status_message = f"{updated}\n\n本日の新着ニュースがあります。"
    else:
        status_message = (
            f"{updated}\n\n本日の新ニュースはありませんでした。\n"
            f"{run_jst:%Y/%m/%d} 時点で取得済みの最新ニュースを表示しています。"
        )
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    env.filters["date_ja"] = _date_ja
    return env.from_string(TEMPLATE).render(
        products=PRODUCTS,
        grouped=grouped,
        errors=errors,
        status_message=status_message,
        new_count=new_count,
    )


def write_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
