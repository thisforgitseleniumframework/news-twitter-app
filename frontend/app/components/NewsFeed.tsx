'use client';

import { NewsArticle } from '../types';

const API_BASE = 'http://localhost:8000';

const CATEGORY_BADGE: Record<string, { label: string; className: string }> = {
  india: {
    label: '🇮🇳 India',
    className: 'bg-orange-950/80 text-orange-300 border border-orange-800/60',
  },
  global: {
    label: '🌍 Global',
    className: 'bg-sky-950/80 text-sky-300 border border-sky-800/60',
  },
  science: {
    label: '🔬 Science',
    className: 'bg-purple-950/80 text-purple-300 border border-purple-800/60',
  },
  technology: {
    label: '💻 Tech',
    className: 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/60',
  },
  space: {
    label: '🚀 Space',
    className: 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/60',
  },
  ocean: {
    label: '🌊 Ocean',
    className: 'bg-teal-950/80 text-teal-300 border border-teal-800/60',
  },
  facts: {
    label: '💡 Facts',
    className: 'bg-yellow-950/80 text-yellow-300 border border-yellow-800/60',
  },
  sports: {
    label: '🏆 Sports',
    className: 'bg-green-950/80 text-green-300 border border-green-800/60',
  },
  sports_local: {
    label: '🇮🇳 Local sports',
    className: 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60',
  },
  sports_international: {
    label: '🌐 Int’l sports',
    className: 'bg-teal-950/80 text-teal-300 border border-teal-800/60',
  },
  sports_laliga: {
    label: '🇪🇸 La Liga',
    className: 'bg-red-950/80 text-red-300 border border-red-800/60',
  },
  sports_epl: {
    label: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL',
    className: 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/60',
  },
  sports_tennis: {
    label: '🎾 Tennis',
    className: 'bg-lime-950/80 text-lime-300 border border-lime-800/60',
  },
  sports_cricket: {
    label: '🏏 Cricket',
    className: 'bg-amber-950/80 text-amber-300 border border-amber-800/60',
  },
};

function categoryBadge(category: string) {
  return (
    CATEGORY_BADGE[category] || {
      label: category,
      className: 'bg-gray-800 text-gray-400 border border-gray-700',
    }
  );
}

interface Props {
  articles: NewsArticle[];
  onGenerateTweet: (id: number, format?: 'auto' | 'single' | 'thread') => void;
  generatingId: number | null;
}

function mediaSrc(article: NewsArticle): string | null {
  if (article.media_url) {
    return article.media_url.startsWith('http')
      ? article.media_url
      : `${API_BASE}${article.media_url}`;
  }
  if (article.media_path) {
    return `${API_BASE}/media/${article.media_path}`;
  }
  return null;
}

export default function NewsFeed({ articles, onGenerateTweet, generatingId }: Props) {
  if (articles.length === 0) {
    return (
      <div className="app-card-static p-12 text-center border-dashed">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/10 text-2xl">
          📰
        </div>
        <p className="text-gray-300 text-base font-medium">No articles yet</p>
        <p className="text-gray-500 text-sm mt-1.5 max-w-xs mx-auto">
          Click <span className="text-sky-400">Fetch Latest News</span> in the header to load the
          feed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-1 scrollbar-thin">
      {articles.map((article, idx) => {
        const src = mediaSrc(article);
        const isHero = idx === 0 && article.is_breaking;
        const badge = categoryBadge(article.category);

        return (
          <article
            key={article.id}
            className={`group relative overflow-hidden rounded-2xl border p-4 transition-all duration-200 ${
              article.is_breaking
                ? 'border-red-500/40 bg-gradient-to-br from-red-950/40 via-gray-900 to-gray-900 shadow-[0_0_0_1px_rgba(239,68,68,0.15)]'
                : 'border-gray-800 bg-gray-900/80 hover:border-gray-600 hover:bg-gray-900 hover:shadow-glow'
            } ${isHero ? 'md:p-5' : ''}`}
          >
            {article.is_breaking && (
              <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-red-600 via-orange-500 to-red-600" />
            )}

            <div className={`flex items-start gap-3 ${isHero && src ? 'md:gap-4' : ''}`}>
              {src && (
                <div
                  className={`shrink-0 overflow-hidden rounded-xl bg-gray-800 border border-gray-700/80 ${
                    isHero ? 'w-24 h-24 md:w-28 md:h-28' : 'w-18 h-18 w-[4.5rem] h-[4.5rem]'
                  }`}
                >
                  {article.media_type === 'video' ? (
                    <video
                      src={src}
                      className="w-full h-full object-cover"
                      muted
                      playsInline
                    />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={src} alt="" className="w-full h-full object-cover" />
                  )}
                </div>
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                  {article.is_breaking && (
                    <span
                      className="text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wide bg-red-600 text-white shadow-sm"
                      title={(article.priority_reasons || []).join(', ')}
                    >
                      BREAKING
                    </span>
                  )}
                  {typeof article.priority_score === 'number' &&
                    article.priority_score >= 25 &&
                    !article.is_breaking && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                        High priority
                      </span>
                    )}
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${badge.className}`}
                  >
                    {badge.label}
                  </span>
                  <span className="text-[11px] text-gray-500 truncate">{article.source}</span>
                </div>

                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`font-semibold text-gray-50 hover:text-sky-300 line-clamp-2 leading-snug transition-colors ${
                    isHero ? 'text-base md:text-lg' : 'text-sm'
                  }`}
                >
                  {article.title}
                </a>

                {article.summary && (
                  <p className="text-xs text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">
                    {article.summary}
                  </p>
                )}
              </div>

              <div className="shrink-0 flex flex-col items-end gap-1.5">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onGenerateTweet(article.id, 'single')}
                    disabled={generatingId === article.id}
                    title="One long-form post: consolidates multiple sources, 250–500 words. Not a thread."
                    className={`text-xs px-3.5 py-2 rounded-xl font-semibold transition-all ${
                      generatingId === article.id
                        ? 'bg-amber-500/20 text-amber-300 cursor-wait border border-amber-500/30'
                        : article.is_processed
                        ? 'bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/40'
                        : 'btn-primary !px-3.5 !py-2 !text-xs shadow-none'
                    }`}
                  >
                    {generatingId === article.id
                      ? 'AI…'
                      : article.is_processed
                      ? 'Tweet again'
                      : 'Tweet'}
                  </button>
                  <button
                    type="button"
                    onClick={() => onGenerateTweet(article.id, 'thread')}
                    disabled={generatingId === article.id}
                    title="Optional 2–3 tweet thread (hook → fact → why it matters)"
                    className="text-xs px-2.5 py-2 rounded-xl font-semibold transition-all bg-violet-500/15 hover:bg-violet-500/25 text-violet-300 border border-violet-500/40 disabled:opacity-50 disabled:cursor-wait"
                  >
                    Thread
                  </button>
                </div>
                <span className="text-[10px] text-gray-600 text-right max-w-[9rem] leading-tight">
                  Tweet = single · Thread = multi
                </span>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
