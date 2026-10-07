import type { CSSProperties } from "react";
import { productColor } from "../lib/format";
import { ALL, EMPTY_FILTERS, filtersActive } from "../lib/news";
import type { Filters } from "../types";

interface Props {
  filters: Filters;
  products: string[];
  productCounts: Record<string, number>;
  months: string[];
  onChange: (filters: Filters) => void;
}

export function FilterBar({ filters, products, productCounts, months, onChange }: Props) {
  const update = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

  return (
    <section className="filters" aria-label="ニュースフィルタ">
      <div className="filter-top">
        <div className="search">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="search"
            value={filters.search}
            placeholder="タイトル・要約を検索"
            aria-label="検索"
            onChange={(event) => update({ search: event.target.value })}
          />
          {filtersActive(filters) && (
            <button type="button" className="reset" onClick={() => onChange(EMPTY_FILTERS)}>
              リセット
            </button>
          )}
        </div>
        <label className="month">
          <span className="visually-hidden">月</span>
          <select value={filters.month} onChange={(event) => update({ month: event.target.value })}>
            <option value={ALL}>全期間</option>
            {months.map((month) => (
              <option key={month} value={month}>
                {month.replace("-", "/")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chips" role="group" aria-label="プロダクト">
        {[ALL, ...products].map((product) => {
          const active = filters.product === product;
          const style =
            product === ALL ? undefined : ({ "--chip": productColor(product) } as CSSProperties);
          return (
            <button
              key={product}
              type="button"
              className={active ? "chip is-active" : "chip"}
              aria-pressed={active}
              style={style}
              onClick={() => update({ product })}
            >
              {product !== ALL && <span className="chip-dot" aria-hidden="true" />}
              {product === ALL ? "All" : product}
              {product !== ALL && <span className="chip-count">{productCounts[product] ?? 0}</span>}
            </button>
          );
        })}
      </div>
    </section>
  );
}
