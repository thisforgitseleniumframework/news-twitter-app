'use client';

import { useCallback, useEffect, useState } from 'react';

const API_BASE = 'http://localhost:8000';

export interface TrendItem {
  name: string;
  query: string;
  rank: number;
}

interface TrendsResponse {
  fetched_at: string | null;
  source?: string | null;
  trends: TrendItem[];
  error?: string | null;
  message?: string | null;
  scraping?: boolean;
  started?: boolean;
  success?: boolean;
}

interface GenerateResult {
  rank?: number;
  trend: string;
  query: string;
  status: string;
  mode?: string;
  reason?: string;
  draft_id?: number;
  tweet_text?: string;
  article_title?: string | null;
}

interface GenerateResponse {
  success: boolean;
  message: string;
  created: number;
  skipped: number;
  news_backed?: number;
  trend_only?: number;
  results: GenerateResult[];
}

interface Props {
  selectedQuery: string | null;
  onSelectTrend: (query: string, label: string) => void;
  onClear: () => void;
  /** Called after drafts are created so parent can switch to Drafts tab */
  onDraftsCreated?: (info: { created: number; message: string }) => void;
}

export default function TrendsBar({
  selectedQuery,
  onSelectTrend,
  onClear,
  onDraftsCreated,
}: Props) {
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [matchCount, setMatchCount] = useState<number | null>(null);

  const [topN, setTopN] = useState(5);
  const [newsOnly, setNewsOnly] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genMessage, setGenMessage] = useState('');
  const [genResults, setGenResults] = useState<GenerateResult[]>([]);
  const [expanded, setExpanded] = useState(true);

  const loadTrends = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trends/`);
      if (res.ok) {
        const json = (await res.json()) as TrendsResponse;
        setData(json);
        setError(json.error || '');
      }
    } catch {
      setError('Cannot reach backend for trends.');
    }
  }, []);

  useEffect(() => {
    loadTrends();
  }, [loadTrends]);

  // Poll while scrape is running
  useEffect(() => {
    if (!data?.scraping && !loading) return;
    const id = setInterval(() => {
      loadTrends();
    }, 3000);
    return () => clearInterval(id);
  }, [data?.scraping, loading, loadTrends]);

  useEffect(() => {
    if (!selectedQuery) {
      setMatchCount(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/trends/match?query=${encodeURIComponent(selectedQuery)}&limit=1`
        );
        if (res.ok && !cancelled) {
          const json = await res.json();
          setMatchCount(json.match_count ?? 0);
        }
      } catch {
        if (!cancelled) setMatchCount(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedQuery]);

  const handleRefresh = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/trends/refresh?headed=true`, {
        method: 'POST',
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(json.detail || json.error || 'Failed to start trend scrape');
      } else {
        setData((prev) => ({
          ...(prev || { trends: [], fetched_at: null }),
          ...json,
          scraping: true,
        }));
      }
      setTimeout(loadTrends, 5000);
    } catch {
      setError('Failed to refresh trends. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDrafts = async () => {
    setGenerating(true);
    setGenMessage('');
    setGenResults([]);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/trends/generate-drafts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ top_n: topN, news_only: newsOnly }),
      });
      const json = (await res.json().catch(() => ({}))) as GenerateResponse & {
        detail?: string;
      };
      if (!res.ok) {
        setError(
          typeof json.detail === 'string'
            ? json.detail
            : 'Failed to generate trend drafts'
        );
        return;
      }
      setGenMessage(json.message || `Created ${json.created} draft(s)`);
      setGenResults(json.results || []);
      onDraftsCreated?.({
        created: json.created || 0,
        message: json.message || '',
      });
    } catch {
      setError('Failed to generate drafts. Check backend and GEMINI_API_KEY.');
    } finally {
      setGenerating(false);
    }
  };

  const trends = data?.trends || [];
  const fetchedLabel = data?.fetched_at
    ? new Date(data.fetched_at).toLocaleString()
    : 'never';

  return (
    <div className="app-card-static p-3.5 mb-4 space-y-3 shadow-sm">
      {/* Header + scrape */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-2 min-w-0 text-left group"
        >
          <span className="text-sm font-semibold text-gray-100 group-hover:text-sky-300 transition-colors">
            🔥 X Trends
          </span>
          <span className="text-[11px] text-gray-500 truncate hidden sm:inline">
            updated {fetchedLabel}
          </span>
          {(loading || data?.scraping) && (
            <span className="text-[11px] text-amber-400 animate-pulse">scraping…</span>
          )}
          <span className="text-[10px] text-gray-600 ml-1">{expanded ? '▾' : '▸'}</span>
        </button>
        <div className="flex items-center gap-2">
          {selectedQuery && (
            <button
              type="button"
              onClick={onClear}
              className="text-xs px-2.5 py-1 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700"
            >
              Clear filter
              {matchCount !== null ? ` (${matchCount} news)` : ''}
            </button>
          )}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading || !!data?.scraping}
            className="text-xs px-3 py-1.5 rounded-xl font-semibold bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-50 disabled:cursor-wait shadow-sm"
            title="Opens Chromium with your saved X login and scrapes Explore/Trending"
          >
            {loading || data?.scraping ? 'Scraping…' : '↻ Refresh from X'}
          </button>
        </div>
      </div>

      {!expanded ? (
        trends.length > 0 && (
          <div className="flex flex-wrap gap-1.5 opacity-90">
            {trends.slice(0, 6).map((t) => (
              <button
                key={`mini-${t.rank}-${t.query}`}
                type="button"
                onClick={() => onSelectTrend(t.query, t.name)}
                className="text-[11px] px-2 py-0.5 rounded-full border border-gray-700 text-gray-400 hover:border-sky-600 hover:text-sky-300"
              >
                {t.name}
              </button>
            ))}
            {trends.length > 6 && (
              <button
                type="button"
                onClick={() => setExpanded(true)}
                className="text-[11px] text-sky-500 px-1"
              >
                +{trends.length - 6} more
              </button>
            )}
          </div>
        )
      ) : (
        <>

      {error && (
        <p className="text-xs text-amber-400/90 leading-relaxed">{error}</p>
      )}

      {trends.length === 0 ? (
        <p className="text-xs text-gray-500">
          No trends yet. Click <strong className="text-gray-400">Refresh from X</strong>.
          Log in once in the browser window if asked (same profile as browser posting).
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {trends.map((t) => {
            const active =
              selectedQuery &&
              selectedQuery.toLowerCase() === t.query.toLowerCase();
            return (
              <button
                key={`${t.rank}-${t.query}`}
                type="button"
                onClick={() => onSelectTrend(t.query, t.name)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  active
                    ? 'bg-sky-600 text-white border-sky-500'
                    : 'bg-gray-950 text-gray-300 border-gray-700 hover:border-sky-700 hover:text-white'
                }`}
                title={`Filter news for: ${t.query}`}
              >
                <span className="text-gray-500 mr-1">#{t.rank}</span>
                {t.name.startsWith('#') ? t.name : t.name}
              </button>
            );
          })}
        </div>
      )}

      {/* Generate drafts from top trends */}
      <div className="border-t border-gray-800 pt-3 mt-1">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-gray-100">
              ✍️ Generate drafts from top trends
            </h3>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed max-w-xl">
              Creates AI tweet drafts for the top N hashtags. Uses matching news when
              available; otherwise a cautious trend-only post (no invented facts).
            </p>
          </div>
          <button
            type="button"
            onClick={handleGenerateDrafts}
            disabled={generating || trends.length === 0}
            className="text-xs px-3 py-2 rounded-lg font-semibold bg-violet-700 hover:bg-violet-600 text-white disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {generating
              ? 'Generating…'
              : `Generate top ${topN} drafts`}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-2.5">
          <label className="flex items-center gap-2 text-xs text-gray-400">
            Top N
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              disabled={generating}
              className="bg-gray-800 border border-gray-700 text-gray-200 rounded-md px-2 py-1 text-xs"
            >
              {[3, 5, 7, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={newsOnly}
              onChange={(e) => setNewsOnly(e.target.checked)}
              disabled={generating}
              className="rounded border-gray-600"
            />
            News only (skip trends with no article match)
          </label>
        </div>

        {genMessage && (
          <p className="text-xs text-emerald-400/90 mt-2">{genMessage}</p>
        )}

        {genResults.length > 0 && (
          <ul className="mt-2 space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {genResults.map((r, i) => (
              <li
                key={`${r.trend}-${i}`}
                className="text-[11px] border border-gray-800 rounded-lg px-2.5 py-1.5 bg-gray-950/60"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-gray-500">#{r.rank ?? i + 1}</span>
                  <span className="text-gray-200 font-medium">{r.trend}</span>
                  {r.status === 'created' && r.mode === 'news' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900">
                      + news
                    </span>
                  )}
                  {r.status === 'created' && r.mode === 'trend_only' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-900">
                      trend only
                    </span>
                  )}
                  {r.status === 'skipped' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                      skipped
                    </span>
                  )}
                  {r.status === 'error' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-950 text-red-400">
                      error
                    </span>
                  )}
                </div>
                {r.article_title && (
                  <p className="text-gray-500 truncate mt-0.5">{r.article_title}</p>
                )}
                {r.reason && (
                  <p className="text-gray-500 mt-0.5">{r.reason}</p>
                )}
                {r.tweet_text && (
                  <p className="text-gray-400 mt-0.5 line-clamp-2 whitespace-pre-wrap">
                    {r.tweet_text}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="text-[10px] text-gray-600">
        Personal use: scrapes X Explore in your browser session. Review every draft
        before posting — trend-only posts must not invent news.
      </p>
        </>
      )}
    </div>
  );
}
