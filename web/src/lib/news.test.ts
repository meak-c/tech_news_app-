import { describe, expect, it } from "vitest";
import type { NewsItem } from "../types";
import {
  EMPTY_FILTERS,
  FALLBACK_SUMMARY,
  filtersActive,
  groupByDay,
  initialItems,
  isFallback,
  matches,
  monthsOf,
  parseSummary,
  sortByDate,
} from "./news";

function item(overrides: Partial<NewsItem> = {}): NewsItem {
  return {
    id: 1,
    date: "2026-10-06",
    product: "Codex",
    title: "Release",
    summary_ja: "・何が変わったか: 新機能\n・影響: 速くなる\n・注意点: 特になし",
    published_at: "2026-10-06T00:00:00+00:00",
    fetched_at: "2026-10-06T18:10:00+00:00",
    source_name: "Codex Changelog",
    item_url: `https://example.com/${Math.random()}`,
    importance: "medium",
    is_new: false,
    month: "2026-10",
    ...overrides,
  };
}

describe("matches", () => {
  it("フィルタ未指定なら全件一致する", () => {
    expect(filtersActive(EMPTY_FILTERS)).toBe(false);
    expect(matches(item(), EMPTY_FILTERS)).toBe(true);
  });

  it("検索語はスペース区切りのAND条件で大文字小文字を区別しない", () => {
    const target = item({ title: "GPT-5 Release" });
    expect(matches(target, { ...EMPTY_FILTERS, search: "gpt-5 新機能" })).toBe(true);
    expect(matches(target, { ...EMPTY_FILTERS, search: "gpt-5 存在しない" })).toBe(false);
  });

  it("プロダクト・月・重要度で絞り込める", () => {
    const target = item({ product: "Claude", importance: "high" });
    expect(matches(target, { ...EMPTY_FILTERS, product: "Claude" })).toBe(true);
    expect(matches(target, { ...EMPTY_FILTERS, product: "Codex" })).toBe(false);
    expect(matches(target, { ...EMPTY_FILTERS, month: "2026-09" })).toBe(false);
    expect(matches(target, { ...EMPTY_FILTERS, importance: "low" })).toBe(false);
  });
});

describe("initialItems", () => {
  it("新着があれば新着と high 上位を表示する", () => {
    const fresh = item({ is_new: true });
    const high = item({ importance: "high", date: "2026-09-01" });
    const old = item({ date: "2026-08-01" });
    expect(initialItems([old, high, fresh], ["Codex"])).toEqual([fresh, high]);
  });

  it("新着がなければ各プロダクト最新3件を表示する", () => {
    const codex = [1, 2, 3, 4].map((day) => item({ date: `2026-10-0${day}` }));
    const claude = item({ product: "Claude" });
    const result = initialItems([...codex, claude], ["Codex", "Claude"]);
    expect(result).toHaveLength(4);
    expect(result).not.toContain(codex[0]);
  });
});

describe("parseSummary", () => {
  it("3行要約をラベルと本文に分解する", () => {
    expect(parseSummary(item().summary_ja)).toEqual([
      { label: "変更", text: "新機能" },
      { label: "影響", text: "速くなる" },
      { label: "注意", text: "特になし" },
    ]);
  });

  it("本文中の中黒では分割せず、1行にまとまった要約も分解できる", () => {
    const summary = "・何が変わったか: URL許可・拒否パターンを修正 ・影響: 安定する";
    expect(parseSummary(summary)).toEqual([
      { label: "変更", text: "URL許可・拒否パターンを修正" },
      { label: "影響", text: "安定する" },
    ]);
  });

  it("形式外の要約は null を返す", () => {
    expect(parseSummary("ただの文章です。")).toBeNull();
    expect(isFallback(FALLBACK_SUMMARY)).toBe(true);
  });
});

describe("groupByDay / monthsOf", () => {
  it("JSTの日付ごとにまとめて今日・昨日のラベルを付ける", () => {
    const now = new Date("2026-10-07T00:30:00+09:00");
    const groups = groupByDay(
      [
        item({ date: "2026-10-07" }),
        item({ date: "2026-10-06" }),
        item({ date: "2025-12-31" }),
        item({ date: "" }),
      ],
      now,
    );
    expect(groups.map((group) => group.label)).toEqual([
      "今日",
      "昨日",
      "2025年12月31日 (水)",
      "日付不明",
    ]);
  });

  it("月は新しい順に unknown を除いて返す", () => {
    const months = monthsOf([
      item({ month: "2026-09" }),
      item({ month: "unknown" }),
      item({ month: "2026-10" }),
    ]);
    expect(months).toEqual(["2026-10", "2026-09"]);
  });
});

describe("sortByDate", () => {
  it("表示日の新しい順に並べ、同じ日は公開日時の新しい順にする", () => {
    const a = item({ date: "2026-10-07", published_at: "2026-10-06T00:00:00+00:00" });
    const b = item({ date: "2026-10-07", published_at: "2026-10-05T00:00:00+00:00" });
    const c = item({ date: "2026-10-05", published_at: "2026-10-09T00:00:00+00:00" });
    expect(sortByDate([c, b, a])).toEqual([a, b, c]);
  });
});
