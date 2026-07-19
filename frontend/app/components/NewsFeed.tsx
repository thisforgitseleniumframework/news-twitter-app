'use client';

import { NewsArticle } from '../types';

const CATEGORY_STYLES: Record<string, string> = {
  india:      'bg-orange-950 text-orange-400 border border-orange-800',
  global:     'bg-blue-950 text-blue-400 border border-blue-800',
  sports:     'bg-green-950 text-green-400 border border-green-800',
  science:    'bg-purple-950 text-purple-400 border border-purple-800',
  technology: 'bg-cyan-950 text-cyan-400 border border-cyan-800',
  space:      'bg-indigo-950 text-indigo-400 border border-indigo-800',
  ocean:      'bg-teal-950 text-teal-400 border border-teal-800',
  facts:      'bg-yellow-950 text-yellow-400 border border-yellow-800',
};

const CATEGORY_LABELS: Record<string, string> = {
  india:      '🇮🇳 India',
  global:     '🌍 Global',
  sports:     '🏆 Sports',
  science:    '🔬 Science',
  technology: '💻 Tech',
  space:      '🚀 Space',
  ocean:      '🌊 Ocean',
  facts:      '💡 Facts',
};

interface Props {
  articles: NewsArticle[];
  onGenerateTweet: (id: number) => void;
  generatingId: number | null;
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
      {articles.map((article) => (
        <div
          key={article.id}
          className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              {/* Badges */}
              <div className="flex items-center gap-2 mb-1.5">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                    CATEGORY_STYLES[article.category] ?? 'bg-gray-800 text-gray-400 border border-gray-700'
                  }`}
                >
                  {CATEGORY_LABELS[article.category] ?? article.category}
                </span>
                <span className="text-xs text-gray-500 truncate">{article.source}</span>
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

            {/* Generate tweet button */}
            <button
              onClick={() => onGenerateTweet(article.id)}
              disabled={generatingId === article.id || article.is_processed}
              className={`shrink-0 text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                article.is_processed
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : generatingId === article.id
                  ? 'bg-yellow-900 text-yellow-400 cursor-wait animate-pulse'
                  : 'bg-blue-700 hover:bg-blue-600 text-white'
              }`}
            >
              {article.is_processed
                ? '✓ Done'
                : generatingId === article.id
                ? 'AI...'
                : '✍️ Tweet'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
