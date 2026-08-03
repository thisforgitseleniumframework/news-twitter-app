'use client';

interface TweetPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  tweetText: string;
  articleUrl?: string | null;
  mediaSrc?: string | null;
  mediaType?: string | null;
  attachMedia: boolean;
  source?: string | null;
}

/** X Premium long-post limit (must match backend MAX_TWEET_LENGTH). */
const MAX_TWEET_LENGTH = 25000;

/** Rough X URL length in the composer (t.co = 23). */
function displayLength(text: string): number {
  // Count each http(s) URL as 23 chars like X does
  return text
    .replace(/https?:\/\/\S+/gi, 'x'.repeat(23))
    .length;
}

function buildFinalText(tweetText: string, articleUrl?: string | null): string {
  const base = (tweetText || '').trim();
  if (!articleUrl || base.includes(articleUrl)) return base;
  const candidate = `${base} ${articleUrl}`.trim();
  // Match backend: append URL if within Premium max length
  if (candidate.length <= MAX_TWEET_LENGTH) return candidate;
  return base;
}

function linkify(text: string) {
  // Split into parts so URLs and hashtags can be styled
  const parts = text.split(/(https?:\/\/\S+|#\w+)/g);
  return parts.map((part, i) => {
    if (/^https?:\/\//i.test(part)) {
      return (
        <span key={i} className="text-[#1d9bf0] break-all">
          {part}
        </span>
      );
    }
    if (/^#\w+/.test(part)) {
      return (
        <span key={i} className="text-[#1d9bf0]">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function TweetPreviewModal({
  isOpen,
  onClose,
  tweetText,
  articleUrl,
  mediaSrc,
  mediaType,
  attachMedia,
  source,
}: TweetPreviewModalProps) {
  if (!isOpen) return null;

  const finalText = buildFinalText(tweetText, articleUrl);
  const weightedLen = displayLength(finalText);
  const overLimit = weightedLen > MAX_TWEET_LENGTH;
  const isLongForm = finalText.length > 280;
  const showMedia = Boolean(attachMedia && mediaSrc);
  const now = new Date();
  const timeLabel = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const dateLabel = now.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Tweet preview"
    >
      <div
        className="bg-black border border-gray-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <h3 className="text-white font-semibold text-sm">Tweet preview</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg leading-none px-2"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <p className="px-4 pt-3 text-xs text-gray-500">
          Approximate look on X — not a live post.
        </p>

        {/* Fake X post card */}
        <div className="p-4">
          <div className="rounded-2xl border border-gray-800 bg-black p-4">
            {/* Author row */}
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-sky-500 to-blue-700 flex items-center justify-center text-white font-bold text-sm shrink-0">
                NP
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="text-white font-bold text-[15px]">NewsPost</span>
                  <span className="text-gray-500 text-[15px]">@your_handle</span>
                  <span className="text-gray-500 text-[15px]">·</span>
                  <span className="text-gray-500 text-[15px]">now</span>
                </div>

                {/* Body */}
                <p className="text-white text-[15px] leading-snug mt-1 whitespace-pre-wrap break-words max-h-80 overflow-y-auto">
                  {linkify(finalText)}
                </p>

                {/* Media */}
                {showMedia && mediaSrc && (
                  <div className="mt-3 rounded-2xl overflow-hidden border border-gray-800 bg-gray-900">
                    {mediaType === 'video' ? (
                      <video
                        src={mediaSrc}
                        className="w-full max-h-72 object-contain bg-black"
                        controls
                        muted
                        playsInline
                      />
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={mediaSrc}
                        alt="Attached media preview"
                        className="w-full max-h-72 object-cover"
                      />
                    )}
                  </div>
                )}

                {!showMedia && mediaSrc && (
                  <p className="mt-2 text-xs text-amber-500/90">
                    Media exists but “Attach to tweet” is off — it won’t appear on the post.
                  </p>
                )}

                {/* Timestamp + source note */}
                <div className="mt-3 text-[13px] text-gray-500">
                  {timeLabel} · {dateLabel}
                  {source ? ` · via ${source}` : ''}
                </div>

                {/* Engagement placeholders */}
                <div className="mt-3 flex justify-between max-w-sm text-gray-500 text-sm pt-1">
                  <span title="Replies">💬</span>
                  <span title="Reposts">🔁</span>
                  <span title="Likes">❤️</span>
                  <span title="Views">📊</span>
                  <span title="Share">↗</span>
                </div>
              </div>
            </div>
          </div>

          {/* Meta footer */}
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
            <span className={overLimit ? 'text-red-400 font-semibold' : 'text-gray-400'}>
              {weightedLen.toLocaleString()} / {MAX_TWEET_LENGTH.toLocaleString()}
              {overLimit ? ' — over limit' : ' chars (URL-weighted estimate)'}
            </span>
            {isLongForm && !overLimit && (
              <span className="text-sky-400">✨ Premium long post</span>
            )}
            {showMedia && (
              <span className="text-emerald-400">
                {mediaType === 'video' ? '🎬 Video attached' : '🖼️ Image attached'}
              </span>
            )}
            {articleUrl && finalText.includes(articleUrl) && (
              <span className="text-sky-400">🔗 Article link included</span>
            )}
            {articleUrl && !finalText.includes(articleUrl) && (
              <span className="text-amber-400">
                ⚠️ Article URL omitted (would exceed {MAX_TWEET_LENGTH.toLocaleString()} chars)
              </span>
            )}
          </div>
        </div>

        <div className="px-4 pb-4 flex justify-end">
          <button
            onClick={onClose}
            className="text-sm px-4 py-2 rounded-full bg-white text-black font-semibold hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
