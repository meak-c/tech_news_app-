const DATE_TIME = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const TIME = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
});
const HERO_DATE = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Tokyo",
  month: "short",
  day: "2-digit",
  weekday: "short",
});

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null | undefined): string {
  const date = toDate(value);
  return date ? DATE_TIME.format(date) : "不明";
}

export function formatTime(value: string | null | undefined): string {
  const date = toDate(value);
  return date ? TIME.format(date) : "--:--";
}

/** ヘッダー用の日付パーツ(例: { weekday: "Wed", month: "Oct", day: "07" })。 */
export function heroDate(value: string | null | undefined): Record<string, string> {
  const date = toDate(value) ?? new Date();
  return Object.fromEntries(
    HERO_DATE.formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
}

/** プロダクトごとのアクセント色。未知のプロダクトは名前から色相を決める。 */
const PRODUCT_COLORS: Record<string, string> = {
  ChatGPT: "#19c37d",
  Claude: "#e8825a",
  "Claude Code": "#b48cff",
  Codex: "#38bdf8",
  Gemini: "#6c8cff",
};

export function productColor(product: string): string {
  if (PRODUCT_COLORS[product]) return PRODUCT_COLORS[product];
  let hash = 0;
  for (const char of product) hash = (hash * 31 + char.charCodeAt(0)) % 360;
  return `hsl(${hash} 70% 62%)`;
}
