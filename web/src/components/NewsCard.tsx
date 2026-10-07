import { useId, useState, type CSSProperties } from "react";
import { formatDateTime, productColor } from "../lib/format";
import { isFallback, parseSummary } from "../lib/news";
import type { NewsItem } from "../types";

interface Props {
  item: NewsItem;
}

export function NewsCard({ item }: Props) {
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  const fallback = isFallback(item.summary_ja);
  const lines = fallback ? null : parseSummary(item.summary_ja);
  const lead = lines ? lines[0].text : item.summary_ja;

  return (
    <article
      className={`card${open ? " is-open" : ""}${item.is_new ? " is-new" : ""}`}
      style={{ "--product": productColor(item.product) } as CSSProperties}
    >
      <button
        type="button"
        className="card-head"
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="card-meta">
          <span className="product">
            <span className="product-dot" aria-hidden="true" />
            {item.product}
          </span>
          {item.is_new && <span className="new-badge">NEW</span>}
        </span>
        <span className="card-title">{item.title}</span>
        <span className={fallback ? "card-lead is-fallback" : "card-lead"}>{lead}</span>
        <span className="card-chevron" aria-hidden="true" />
      </button>

      <div className="card-body" id={detailsId} hidden={!open}>
        {lines ? (
          <dl className="summary">
            {lines.map((line, index) => (
              <div key={index}>
                <dt>{line.label}</dt>
                <dd>{line.text}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className={fallback ? "summary-plain is-fallback" : "summary-plain"}>
            {item.summary_ja}
          </p>
        )}
        <div className="card-foot">
          <span className="source">
            {item.source_name} · 取得 {formatDateTime(item.fetched_at)}
          </span>
          <a className="official" href={item.item_url} target="_blank" rel="noopener noreferrer">
            公式ページ
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </div>
    </article>
  );
}
