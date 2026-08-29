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
  isThread?: boolean;
  threadParts?: string[] | null;
}

/** Single-post limit (must match backend MAX_TWEET_LENGTH for 250–500 words). */
const MAX_TWEET_LENGTH = 3500;

/** Rough X URL length in the composer (t.co = 23). */
function displayLength(text: string): number {
  return text
    .replace(/https?:\/\/\S+/gi, 'x'.repeat(23))
    .length;
}

function buildFinalText(tweetText: string, articleUrl?: string | null): string {
  const base = (tweetText || '').trim();
  if (!articleUrl || base.includes(articleUrl)) return base;
  const candidate = `${base} ${articleUrl}`.trim();
  if (candidate.length <= MAX_TWEET_LENGTH) return candidate;
  return base;
}

function linkify(text: string) {
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

function ThreadTweetCard({
  text,
  index,
  total,
  showMedia,
  mediaSrc,
  mediaType,
  isFirst,
}: {
  text: string;
  index: number;
  total: number;
  showMedia: boolean;
  mediaSrc?: string | null;
  mediaType?: string | null;
  isFirst: boolean;
}) {
  return (
    <div className="relative flex gap-3">
      <div className="flex flex-col items-center shrink-0">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-sky-500 to-blue-700 flex items-center justify-center text-white font-bold text-sm">
          NP
        </div>
        {index < total && (
          <div className="w-0.5 flex-1 min-h-[16px] bg-gray-700 my-1" />
        )}
      </div>
      <div className="flex-1 min-w-0 pb-4">
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-white font-bold text-[15px]">NewsPost</span>
          <span className="text-gray-500 text-[15px]">@your_handle</span>
          <span className="text-gray-500 text-[13px]">· {index}/{total}</span>
        </div>
        <p className="text-white text-[15px] leading-snug mt-1 whitespace-pre-wrap break-words">
          {linkify(text)}
        </p>
        {isFirst && showMedia && mediaSrc && (
          <div className="mt-3 rounded-2xl overflow-hidden border border-gray-800 bg-gray-900">
            {mediaType === 'video' ? (
              <video
                src={mediaSrc}
                className="w-full max-h-56 object-contain bg-black"
                controls
                muted
                playsInline
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaSrc}
                alt="Attached media preview"
                className="w-full max-h-56 object-cover"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
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
  isThread = false,
  threadParts = null,
}: TweetPreviewModalProps) {
  if (!isOpen) return null;

  const parts =
    isThread && threadParts && threadParts.length >= 2
      ? threadParts.map((p) => p.trim()).filter(Boolean)
      : null;

  const finalText = buildFinalText(tweetText, articleUrl);
  const firstWithUrl =
    parts && parts.length
      ? buildFinalText(parts[0], articleUrl)
      : finalText;
  const weightedLen = parts
    ? parts.reduce(
        (sum, p, i) =>
          sum + displayLength(i === 0 ? firstWithUrl : p),
        0
      )
    : displayLength(finalText);
  const overLimit = parts
    ? parts.some(
        (p, i) =>
          displayLength(i === 0 ? firstWithUrl : p) > MAX_TWEET_LENGTH
      )
    : weightedLen > MAX_TWEET_LENGTH;
  const isLongForm = !parts && finalText.length > 280; // show long-form badge when past classic limit
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
        className="bg-black border border-gray-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
          <h3 className="text-white font-semibold text-sm">
            {parts ? 'Thread preview' : 'Tweet preview'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg leading-none px-2"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <p className="px-4 pt-3 text-xs text-gray-500 shrink-0">
          Approximate look on X — not a live post.
          {parts ? ` · ${parts.length}-tweet thread` : ''}
        </p>

        <div className="p-4 overflow-y-auto flex-1">
          {parts ? (
            <div className="rounded-2xl border border-gray-800 bg-black p-4">
              {parts.map((part, i) => (
                <ThreadTweetCard
                  key={i}
                  text={i === 0 ? firstWithUrl : part}
                  index={i + 1}
                  total={parts.length}
                  showMedia={showMedia}
                  mediaSrc={mediaSrc}
                  mediaType={mediaType}
                  isFirst={i === 0}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-gray-800 bg-black p-4">
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

                  <p className="text-white text-[15px] leading-snug mt-1 whitespace-pre-wrap break-words max-h-80 overflow-y-auto">
                    {linkify(finalText)}
                  </p>

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

                  <div className="mt-3 text-[13px] text-gray-500">
                    {timeLabel} · {dateLabel}
                    {source ? ` · via ${source}` : ''}
                  </div>

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
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
            {parts ? (
              <>
                <span className="text-violet-400 font-semibold">
                  🧵 {parts.length} tweets
                </span>
                {parts.map((p, i) => {
                  const len = displayLength(i === 0 ? firstWithUrl : p);
                  const over = len > MAX_TWEET_LENGTH;
                  return (
                    <span
                      key={i}
                      className={over ? 'text-red-400 font-semibold' : 'text-gray-400'}
                    >
                      {i + 1}: {len.toLocaleString()} chars
                    </span>
                  );
                })}
              </>
            ) : (
              <span className={overLimit ? 'text-red-400 font-semibold' : 'text-gray-400'}>
                {weightedLen.toLocaleString()} / {MAX_TWEET_LENGTH.toLocaleString()}
                {overLimit ? ' — over limit' : ' chars (URL-weighted estimate)'}
              </span>
            )}
            {isLongForm && !overLimit && (
              <span className="text-sky-400">✨ Premium long post</span>
            )}
            {showMedia && (
              <span className="text-emerald-400">
                {mediaType === 'video' ? '🎬 Video on tweet 1' : '🖼️ Image on tweet 1'}
              </span>
            )}
            {articleUrl && firstWithUrl.includes(articleUrl) && (
              <span className="text-sky-400">🔗 Article link on tweet 1</span>
            )}
          </div>
        </div>

        <div className="px-4 pb-4 flex justify-end shrink-0">
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
