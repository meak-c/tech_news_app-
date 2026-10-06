import { useState } from "react";
import { formatTime, heroDate } from "../lib/format";
import type { NewsPayload } from "../types";

interface Props {
  payload: NewsPayload;
}

export function Header({ payload }: Props) {
  const [showErrors, setShowErrors] = useState(false);
  const date = heroDate(payload.generated_at);
  const hasNew = payload.new_count > 0;

  return (
    <header className="hero">
      <div className="hero-top">
        <p className="eyebrow">
          <span className="pulse" aria-hidden="true" />
          Official release notes only
        </p>
        <time className="hero-date" dateTime={payload.generated_at}>
          <span className="hero-weekday">{date.weekday}</span>
          <span className="hero-day">
            {date.month} {date.day}
          </span>
        </time>
      </div>

      <h1 className="hero-title">
        Tech News
        <span>Morning</span>
      </h1>

      <p className="hero-lead">
        {hasNew
          ? `今朝は ${payload.new_count} 件の新着があります。`
          : "本日の新ニュースはありませんでした。最近の注目ニュースを表示しています。"}
      </p>

      <dl className="stats">
        <div className={hasNew ? "stat stat-accent" : "stat"}>
          <dt>新着</dt>
          <dd>{payload.new_count}</dd>
        </div>
        <div className="stat">
          <dt>総件数</dt>
          <dd>{payload.items.length}</dd>
        </div>
        <div className="stat">
          <dt>更新</dt>
          <dd>{formatTime(payload.generated_at)}</dd>
        </div>
      </dl>

      {payload.errors.length > 0 && (
        <section className="alert" aria-label="取得エラー">
          <button
            type="button"
            className="alert-toggle"
            aria-expanded={showErrors}
            onClick={() => setShowErrors((open) => !open)}
          >
            <span>⚠ {payload.errors.length} 件のソース取得に失敗しました</span>
            <span className="alert-chevron" aria-hidden="true">
              {showErrors ? "−" : "+"}
            </span>
          </button>
          {showErrors && (
            <ul>
              {payload.errors.map((error) => (
                <li key={error.source_name}>
                  <strong>{error.source_name}</strong>
                  <span>{error.message}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </header>
  );
}
