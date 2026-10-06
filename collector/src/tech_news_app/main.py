from __future__ import annotations

import argparse
import json
from collections.abc import Collection
from datetime import UTC, datetime

from .config import Settings
from .exporter import write_news_json
from .fetchers import NewsFetcher
from .models import FetchedItem, NewsItem, RunLog
from .storage import NewsStorage
from .summarizer import Summarizer, needs_resummary

# 取得対象外になった過去記事の再要約は、無料枠を考慮して1回の実行あたりの件数を制限する。
BACKFILL_LIMIT = 50


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an official tech news digest.")
    parser.add_argument("--no-llm", action="store_true", help="Do not call Gemini API.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print results without updating the DB or writing news.json.",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Write news.json from the existing DB without fetching or summarizing.",
    )
    parser.add_argument("--output", help="Override the generated news.json path.")
    return parser


def _to_fetched(item: NewsItem) -> FetchedItem:
    return FetchedItem(
        product=item.product,
        source_name=item.source_name,
        source_url=item.source_url,
        item_url=item.item_url,
        title=item.title,
        published_at=item.published_at,
        raw_text=item.raw_text,
    )


def backfill_summaries(
    storage: NewsStorage,
    summarizer: Summarizer,
    skip_ids: Collection[int | None] = (),
    limit: int = BACKFILL_LIMIT,
) -> int:
    """未要約のまま保存されている記事を新しい順に再要約し、成功件数を返す。"""
    if not summarizer.use_llm:
        return 0
    targets = [
        item
        for item in storage.all_news()
        if item.id not in skip_ids and needs_resummary(item.summary_ja)
    ][:limit]
    updated = 0
    for item in targets:
        summary = summarizer.summarize(_to_fetched(item))
        if needs_resummary(summary):
            # API障害やレート制限の可能性が高いため、以降の呼び出しは次回実行に回す。
            break
        storage.update_summary(item.id, summary)
        updated += 1
    return updated


def export_only(settings: Settings) -> int:
    with NewsStorage(settings.db_path) as storage:
        latest = storage.all_news()
    write_news_json(settings.output_path, latest, [], datetime.now(UTC), 0)
    print(f"Exported {len(latest)} item(s) to {settings.output_path}.")
    return 0 if latest else 1


def run(
    no_llm: bool = False,
    dry_run: bool = False,
    output: str | None = None,
    export: bool = False,
) -> int:
    settings = Settings.from_env(output_override=output)
    if export:
        return export_only(settings)
    run_at = datetime.now(UTC)
    fetched_items, errors = NewsFetcher(settings).fetch_all()

    if dry_run:
        print(
            json.dumps(
                {
                    "item_count": len(fetched_items),
                    "items": [item.model_dump(mode="json") for item in fetched_items],
                    "errors": [error.model_dump() for error in errors],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if fetched_items else 1

    summarizer = Summarizer(settings, use_llm=not no_llm)
    with NewsStorage(settings.db_path) as storage:
        existing = storage.find_existing(fetched_items)
        saved_items = []
        new_count = 0
        for fetched in fetched_items:
            previous = existing.get(fetched.item_url)
            if previous is not None and not needs_resummary(previous.summary_ja):
                summary = previous.summary_ja
            else:
                summary = summarizer.summarize(fetched)
            saved, is_new = storage.save_item(fetched, summary)
            saved_items.append(saved)
            new_count += int(is_new)

        backfilled = backfill_summaries(
            storage, summarizer, skip_ids={item.id for item in saved_items}
        )

        latest = storage.all_news()
        new_ids = {item.id for item in saved_items if item.is_new}
        for item in latest:
            item.is_new = item.id in new_ids

        if errors and fetched_items:
            status = "partial_success"
        elif errors:
            status = "failed"
        else:
            status = "success"
        error_message = "; ".join(f"{e.source_name}: {e.message}" for e in errors) or None
        storage.add_run_log(
            RunLog(
                run_at=run_at,
                status=status,
                new_item_count=new_count,
                error_message=error_message,
            )
        )
    write_news_json(settings.output_path, latest, errors, run_at, new_count)
    print(
        f"Generated {settings.output_path} with {new_count} new item(s); "
        f"{backfilled} backfilled summary(ies); {len(errors)} source error(s)."
    )
    return 0 if fetched_items or latest else 1


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(
        run(
            no_llm=args.no_llm,
            dry_run=args.dry_run,
            output=args.output,
            export=args.export_only,
        )
    )


if __name__ == "__main__":
    main()
