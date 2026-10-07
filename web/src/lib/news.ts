import type { Filters, NewsItem } from "../types";

export const ALL = "all";
export const FALLBACK_SUMMARY = "要約未生成。公式ページで確認してください。";
export const EMPTY_FILTERS: Filters = { product: ALL, month: ALL, search: "" };

const JST_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

export function filtersActive(filters: Filters): boolean {
  return (
    filters.product !== ALL ||
    filters.month !== ALL ||
    filters.search.trim() !== ""
  );
}

export function matches(item: NewsItem, filters: Filters): boolean {
  if (filters.product !== ALL && item.product !== filters.product) return false;
  if (filters.month !== ALL && item.month !== filters.month) return false;
  const terms = filters.search.toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length) {
    const haystack = `${item.title} ${item.summary_ja} ${item.source_name}`.toLowerCase();
    return terms.every((term) => haystack.includes(term));
  }
  return true;
}

export function itemTime(item: NewsItem): number {
  return Date.parse(item.published_at ?? item.fetched_at) || 0;
}

/** 表示日(JST)の新しい順。同じ日の中は公開日時、取得順の新しい順。 */
export function sortByDate(items: NewsItem[]): NewsItem[] {
  return [...items].sort(
    (a, b) =>
      b.date.localeCompare(a.date) ||
      itemTime(b) - itemTime(a) ||
      (b.id ?? 0) - (a.id ?? 0),
  );
}

/**
 * フィルタ未指定時の初期表示。
 * 新着があれば新着全件、なければ各プロダクトの最新3件。
 */
export function initialItems(items: NewsItem[], products: string[]): NewsItem[] {
  const sorted = sortByDate(items);
  const selected = new Map<string, NewsItem>();
  const add = (item: NewsItem) => selected.set(item.item_url, item);

  const newItems = sorted.filter((item) => item.is_new);
  if (newItems.length) {
    newItems.forEach(add);
  } else {
    for (const product of products) {
      sorted.filter((item) => item.product === product).slice(0, 3).forEach(add);
    }
  }
  return sortByDate([...selected.values()]);
}

export function monthsOf(items: NewsItem[]): string[] {
  return [...new Set(items.map((item) => item.month))]
    .filter((month) => month !== "unknown")
    .sort()
    .reverse();
}

export function isFallback(summary: string): boolean {
  return !summary.trim() || summary.trim() === FALLBACK_SUMMARY;
}

export interface SummaryLine {
  label: string;
  text: string;
}

const SUMMARY_LABELS: Record<string, string> = {
  何が変わったか: "変更",
  影響: "影響",
  注意点: "注意",
};

/**
 * 「・何が変わったか: ...」形式の3行要約を分解する。形式外なら null。
 * 本文中の「許可・拒否」のような中黒では分割しないよう、「・ラベル:」の直前だけで区切る。
 */
export function parseSummary(summary: string): SummaryLine[] | null {
  const lines = summary
    .split(/\n+|(?=・[^・:：\s]{1,12}[:：])/)
    .map((line) => line.trim())
    .filter(Boolean);
  const parsed: SummaryLine[] = [];
  for (const line of lines) {
    const match = /^・\s*([^・:：]{1,12})\s*[:：]\s*(.*)$/.exec(line);
    if (match) {
      const label = match[1].trim();
      parsed.push({ label: SUMMARY_LABELS[label] ?? label, text: match[2].trim() });
    } else if (parsed.length) {
      parsed[parsed.length - 1].text += line;
    } else {
      return null;
    }
  }
  return parsed.length ? parsed : null;
}

export function jstDateKey(value: string | number | Date): string {
  return JST_DATE.format(new Date(value));
}

function dayLabel(key: string, todayKey: string): string {
  const diffDays = Math.round((Date.parse(todayKey) - Date.parse(key)) / 86_400_000);
  if (diffDays === 0) return "今日";
  if (diffDays === 1) return "昨日";
  const [year, month, day] = key.split("-").map(Number);
  const weekday = WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()];
  const sameYear = key.slice(0, 4) === todayKey.slice(0, 4);
  return `${sameYear ? "" : `${year}年`}${month}月${day}日 (${weekday})`;
}

export interface DayGroup {
  key: string;
  label: string;
  items: NewsItem[];
}

/** 日付(JST)ごとにまとめる。items は新しい順に並んでいる前提。 */
export function groupByDay(items: NewsItem[], now: Date = new Date()): DayGroup[] {
  const todayKey = jstDateKey(now);
  const groups: DayGroup[] = [];
  for (const item of items) {
    const key = item.date || "unknown";
    let group = groups.at(-1);
    if (!group || group.key !== key) {
      group = {
        key,
        label: key === "unknown" ? "日付不明" : dayLabel(key, todayKey),
        items: [],
      };
      groups.push(group);
    }
    group.items.push(item);
  }
  return groups;
}
