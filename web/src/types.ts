/** collector(Python)が出力する news.json の1記事。 */
export interface NewsItem {
  id: number | null;
  /** 画面に表示する日付(JST, YYYY-MM-DD)。ベンダー現地の公開日ではなく日本で見える日。 */
  date: string;
  product: string;
  title: string;
  summary_ja: string;
  published_at: string | null;
  fetched_at: string;
  source_name: string;
  item_url: string;
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
  search: string;
}
