'use client';

import { NewsArticle } from '../types';

const API_BASE = 'http://localhost:8000';

const CATEGORY_BADGE: Record<string, { label: string; className: string }> = {
  india: {
    label: '🇮🇳 India',
    className: 'bg-orange-950 text-orange-400 border border-orange-800',
  },
  global: {
    label: '🌍 Global',
    className: 'bg-blue-950 text-blue-400 border border-blue-800',
  },
  science: {
    label: '🔬 Science',
    className: 'bg-purple-950 text-purple-400 border border-purple-800',
  },
  technology: {
    label: '💻 Tech',
    className: 'bg-cyan-950 text-cyan-400 border border-cyan-800',
  },
  space: {
    label: '🚀 Space',
    className: 'bg-indigo-950 text-indigo-400 border border-indigo-800',
  },
  ocean: {
    label: '🌊 Ocean',
    className: 'bg-teal-950 text-teal-400 border border-teal-800',
  },
  facts: {
    label: '💡 Facts',
    className: 'bg-yellow-950 text-yellow-400 border border-yellow-800',
  },
  sports: {
    label: '🏆 Sports',
    className: 'bg-green-950 text-green-400 border border-green-800',
  },
  sports_local: {
    label: '🇮🇳 Local sports',
    className: 'bg-emerald-950 text-emerald-400 border border-emerald-800',
  },
  sports_international: {
    label: '🌐 Int’l sports',
    className: 'bg-teal-950 text-teal-400 border border-teal-800',
  },
  sports_laliga: {
    label: '🇪🇸 La Liga',
    className: 'bg-red-950 text-red-300 border border-red-800',
  },
  sports_epl: {
    label: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL',
    className: 'bg-indigo-950 text-indigo-300 border border-indigo-800',
  },
  sports_tennis: {
    label: '🎾 Tennis',
    className: 'bg-lime-950 text-lime-300 border border-lime-800',
  },
  sports_cricket: {
    label: '🏏 Cricket',
    className: 'bg-amber-950 text-amber-300 border border-amber-800',
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
  onGenerateTweet: (id: number) => void;
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
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center">
        <p className="text-gray-400 text-lg font-medium">No articles yet</p>
        <p className="text-gray-600 text-sm mt-2">
          Click &quot;Fetch Latest News&quot; in the header to load articles.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-[calc(100vh-230px)] overflow-y-auto pr-1">
      {articles.map((article) => {
        const src = mediaSrc(article);
        return (
          <div
            key={article.id}
            className={`bg-gray-900 border rounded-xl p-4 hover:border-gray-700 transition-colors ${
              article.is_breaking
                ? 'border-red-800/80 bg-red-950/20 shadow-[0_0_0_1px_rgba(185,28,28,0.25)]'
                : 'border-gray-800'
            }`}
          >
            <div className="flex items-start gap-3">
              {/* Thumbnail */}
              {src && (
                <div className="shrink-0 w-16 h-16 rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
                  {article.media_type === 'video' ? (
                    <video
                      src={src}
                      className="w-full h-full object-cover"
                      muted
                      playsInline
                    />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={src}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  )}
                </div>
              )}

              <div className="flex-1 min-w-0">
                {/* Badges */}
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {article.is_breaking && (
                    <span
                      className="text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wide bg-red-600 text-white animate-pulse"
                      title={(article.priority_reasons || []).join(', ')}
                    >
                      🚨 BREAKING
                    </span>
                  )}
                  {typeof article.priority_score === 'number' &&
                    article.priority_score >= 25 &&
                    !article.is_breaking && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-950 text-amber-400 border border-amber-800">
                        ⚡ High priority
                      </span>
                    )}
                  {(() => {
                    const badge = categoryBadge(article.category);
                    return (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-semibold ${badge.className}`}
                      >
                        {badge.label}
                      </span>
                    );
                  })()}
                  <span className="text-xs text-gray-500 truncate">{article.source}</span>
                  {src && (
                    <span className="text-xs text-emerald-500 shrink-0">
                      {article.media_type === 'video' ? '🎬' : '🖼️'}
                    </span>
                  )}
                  {typeof article.priority_score === 'number' && (
                    <span
                      className="text-[10px] text-gray-600 ml-auto shrink-0"
                      title="Priority score"
                    >
                      score {article.priority_score}
                    </span>
                  )}
                </div>

                {/* Title */}
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-gray-100 hover:text-blue-400 line-clamp-2 leading-snug transition-colors"
                >
                  {article.title}
                </a>

                {/* Summary */}
                {article.summary && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2 leading-relaxed">
                    {article.summary}
                  </p>
                )}
              </div>

              {/* Generate tweet — can reuse the same news any number of times */}
              <div className="shrink-0 flex flex-col items-end gap-1">
                <button
                  onClick={() => onGenerateTweet(article.id)}
                  disabled={generatingId === article.id}
                  title={
                    article.is_processed
                      ? 'Generate another draft from this news'
                      : 'Generate a tweet draft'
                  }
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                    generatingId === article.id
                      ? 'bg-yellow-900 text-yellow-400 cursor-wait animate-pulse'
                      : article.is_processed
                      ? 'bg-blue-800 hover:bg-blue-700 text-white border border-blue-600'
                      : 'bg-blue-700 hover:bg-blue-600 text-white'
                  }`}
                >
                  {generatingId === article.id
                    ? 'AI...'
                    : article.is_processed
                    ? '✍️ Tweet again'
                    : '✍️ Tweet'}
                </button>
                {article.is_processed && generatingId !== article.id && (
                  <span className="text-[10px] text-gray-500">used before</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
