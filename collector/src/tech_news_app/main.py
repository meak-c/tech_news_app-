from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from .config import Settings
from .fetchers import NewsFetcher
from .models import RunLog
from .renderer import write_site
from .storage import NewsStorage
from .summarizer import Summarizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an official tech news digest.")
    parser.add_argument("--no-llm", action="store_true", help="Do not call Gemini API.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print results without updating the DB or writing HTML.",
    )
    parser.add_argument("--output", help="Override the generated HTML path.")
    return parser


def run(no_llm: bool = False, dry_run: bool = False, output: str | None = None) -> int:
    settings = Settings.from_env(output_override=output)
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
            should_refresh_fallback = (
                previous is not None
                and "自動要約ではありません。" in previous.summary_ja
            )
            if previous is not None and not should_refresh_fallback:
                summary = previous.summary_ja
            else:
                summary = summarizer.summarize(fetched)
            saved, is_new = storage.save_item(fetched, summary)
            saved_items.append(saved)
            new_count += int(is_new)

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
    write_site(settings.output_path, latest, errors, run_at, new_count)
    print(
        f"Generated {settings.output_path} with {new_count} new item(s); "
        f"{len(errors)} source error(s)."
    )
    return 0 if fetched_items or latest else 1


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run(no_llm=args.no_llm, dry_run=args.dry_run, output=args.output))


if __name__ == "__main__":
    main()
