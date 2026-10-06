import { useEffect, useMemo, useState } from "react";
import { FilterBar } from "./components/FilterBar";
import { Header } from "./components/Header";
import { NewsCard } from "./components/NewsCard";
import {
  EMPTY_FILTERS,
  filtersActive,
  groupByDay,
  initialItems,
  matches,
  monthsOf,
  sortByDate,
} from "./lib/news";
import type { Filters, NewsPayload } from "./types";

const PAGE_SIZE = 30;

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; payload: NewsPayload };

export function App() {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [expanded, setExpanded] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}news.json`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`news.json: HTTP ${response.status}`);
        return response.json() as Promise<NewsPayload>;
      })
      .then((payload) => setLoad({ status: "ready", payload }))
      .catch((error: unknown) => setLoad({ status: "error", message: String(error) }));
  }, []);

  const payload = load.status === "ready" ? load.payload : null;
  const items = useMemo(() => sortByDate(payload?.items ?? []), [payload]);
  const products = payload?.products ?? [];
  const months = useMemo(() => monthsOf(items), [items]);
  const productCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const item of items) counts[item.product] = (counts[item.product] ?? 0) + 1;
    return counts;
  }, [items]);

  const active = filtersActive(filters);
  const highlight = !active && !expanded;
  const matched = useMemo(() => items.filter((item) => matches(item, filters)), [items, filters]);
  const visible = useMemo(
    () => (highlight ? initialItems(matched, products) : matched.slice(0, limit)),
    [highlight, matched, products, limit],
  );
  const groups = useMemo(() => groupByDay(visible), [visible]);
  const hasMore = visible.length < matched.length;

  const changeFilters = (next: Filters) => {
    setFilters(next);
    setExpanded(false);
    setLimit(PAGE_SIZE);
  };

  const showMore = () => {
    if (highlight) {
      setExpanded(true);
      setLimit(Math.max(visible.length, PAGE_SIZE) + PAGE_SIZE);
    } else {
      setLimit((value) => value + PAGE_SIZE);
    }
  };

  if (!payload) {
    return (
      <main className="shell">
        <p className={load.status === "error" ? "notice is-error" : "notice"}>
          {load.status === "error"
            ? `ニュースデータの読み込みに失敗しました。(${load.message})`
            : "読み込み中…"}
        </p>
      </main>
    );
  }

  return (
    <main className="shell">
      <Header payload={payload} />
      <FilterBar
        filters={filters}
        products={products}
        productCounts={productCounts}
        months={months}
        onChange={changeFilters}
      />

      <div className="results" aria-live="polite">
        <span className="results-mode">{highlight ? "Highlights" : "All news"}</span>
        <span>
          <strong>{visible.length}</strong> / {matched.length} 件
        </span>
      </div>

      {groups.map((group) => (
        <section key={group.key} className="day" aria-label={group.label}>
          <h2 className="day-label">
            <span>{group.label}</span>
            <span className="day-count">{group.items.length}</span>
          </h2>
          <div className="day-items">
            {group.items.map((item) => (
              <NewsCard key={item.item_url} item={item} />
            ))}
          </div>
        </section>
      ))}

      {matched.length === 0 && <p className="notice">条件に一致するニュースはありません。</p>}

      {hasMore && (
        <button type="button" className="more" onClick={showMore}>
          {highlight ? "すべてのニュースを見る" : "さらに表示"}
          <span>残り {matched.length - visible.length} 件</span>
        </button>
      )}

      <footer className="footer">
        公式または公式に準ずる一次情報のみを掲載しています。要約は Gemini による自動生成です。
      </footer>
    </main>
  );
}
