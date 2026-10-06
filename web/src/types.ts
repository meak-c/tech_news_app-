export type Importance = "high" | "medium" | "low";

/** collector(Python)が出力する news.json の1記事。 */
export interface NewsItem {
  id: number | null;
  product: string;
  title: string;
  summary_ja: string;
  published_at: string | null;
  fetched_at: string;
  source_name: string;
  item_url: string;
  importance: Importance;
  is_new: boolean;
  month: string;
}

export interface SourceError {
  source_name: string;
  message: string;
}

export interface NewsPayload {
  generated_at: string;
  new_count: number;
  products: string[];
  errors: SourceError[];
  items: NewsItem[];
}

export interface Filters {
  product: string;
  month: string;
  importance: "all" | Importance;
  search: string;
}
