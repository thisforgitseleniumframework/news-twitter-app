'use client';

import { useState, useEffect } from 'react';
import { TweetDraft } from '../types';
import ScheduleModal from './ScheduleModal';
import TweetPreviewModal from './TweetPreviewModal';

interface Props {
  draft: TweetDraft;
  onUpdate: () => void;
  apiBase: string;
  selected?: boolean;
  onSelectChange?: (selected: boolean) => void;
  showCheckbox?: boolean;
}

/** X Premium long-post limit (must match backend MAX_TWEET_LENGTH). */
const MAX_TWEET_LENGTH = 25000;

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-yellow-950 text-yellow-400 border-yellow-800',
  approved: 'bg-green-950 text-green-400 border-green-800',
  posted: 'bg-blue-950 text-blue-400 border-blue-800',
  rejected: 'bg-red-950 text-red-500 border-red-900',
  scheduled: 'bg-purple-950 text-purple-400 border-purple-800',
};

function mediaSrc(draft: TweetDraft, apiBase: string): string | null {
  if (draft.media_url) {
    return draft.media_url.startsWith('http')
      ? draft.media_url
      : `${apiBase}${draft.media_url}`;
  }
  if (draft.media_path) {
    return `${apiBase}/media/${draft.media_path}`;
  }
  return null;
}

export default function TweetCard({ draft, onUpdate, apiBase, selected = false, onSelectChange, showCheckbox = false }: Props) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(draft.tweet_text);
  const [loading, setLoading] = useState(false);
  const [postResult, setPostResult] = useState<string>('');
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [attachMedia, setAttachMedia] = useState(Boolean(draft.attach_media && draft.media_path));

  useEffect(() => {
    setAttachMedia(Boolean(draft.attach_media && draft.media_path));
    setEditText(draft.tweet_text);
  }, [draft.id, draft.attach_media, draft.media_path, draft.tweet_text]);

  const charCount = editText.length;
  const isOverLimit = charCount > MAX_TWEET_LENGTH;
  const charRemaining = MAX_TWEET_LENGTH - charCount;
  const src = mediaSrc(draft, apiBase);
  const hasMedia = Boolean(src && draft.media_path);

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tweet_text: editText }),
      });
      if (res.ok) {
        setEditing(false);
        onUpdate();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAttach = async (next: boolean) => {
    if (!hasMedia) return;
    setAttachMedia(next);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attach_media: next }),
      });
      if (!res.ok) {
        setAttachMedia(!next);
        const err = await res.json().catch(() => ({}));
        setPostResult(`❌ ${err.detail || 'Could not update attach preference'}`);
      } else {
        onUpdate();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: 'approve' | 'reject' | 'post') => {
    setLoading(true);
    setPostResult('');
    try {
      const opts: RequestInit = { method: 'POST' };
      if (action === 'post') {
        opts.headers = { 'Content-Type': 'application/json' };
        opts.body = JSON.stringify({ attach_media: attachMedia });
      }
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/${action}`, opts);
      const data = await res.json();
      if (action === 'post') {
        if (data.success) {
          const mediaNote = data.media_attached ? ' (with media)' : '';
          setPostResult(`Posted!${mediaNote} View: ${data.tweet_url}`);
        } else {
          setPostResult(`Error: ${data.error}`);
        }
      }
      onUpdate();
    } finally {
      setLoading(false);
    }
  };

  /** Semi-auto: open X in browser, fill text/media; you click Post. */
  const handleBrowserPost = async () => {
    setLoading(true);
    setPostResult('');
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/post-browser`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attach_media: attachMedia }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setPostResult(
          `🌐 ${data.message || 'Browser opened. Review and click Post on X, then Mark as posted.'}`
        );
      } else {
        setPostResult(`❌ ${data.detail || data.error || 'Could not open browser'}`);
      }
    } catch {
      setPostResult('❌ Failed to reach backend for browser post');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkPosted = async () => {
    setLoading(true);
    setPostResult('');
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/mark-posted`, {
        method: 'POST',
      });
      if (res.ok) {
        setPostResult('✅ Marked as posted');
        onUpdate();
      } else {
        const err = await res.json().catch(() => ({}));
        setPostResult(`❌ ${err.detail || 'Could not mark as posted'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSchedule = async (scheduledAt: string) => {
    setLoading(true);
    try {
      // Persist attach preference before scheduling
      if (hasMedia) {
        await fetch(`${apiBase}/api/tweets/${draft.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ attach_media: attachMedia }),
        });
      }
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scheduled_at: scheduledAt }),
      });
      if (res.ok) {
        setPostResult('✅ Tweet scheduled successfully!');
        setShowScheduleModal(false);
        onUpdate();
      } else {
        const err = await res.json();
        setPostResult(`❌ ${err.detail}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`bg-gray-900 border rounded-xl p-4 transition-colors ${selected ? 'border-blue-500 bg-blue-950/20' : 'border-gray-800 hover:border-gray-700'}`}>
      <div className="flex gap-3">
        {/* Checkbox for batch selection */}
        {showCheckbox && (
          <div className="flex-shrink-0 pt-1">
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onSelectChange?.(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 cursor-pointer"
            />
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs text-gray-500 truncate">{draft.source}</span>
              {draft.category && (
                <span className="text-xs text-gray-600">·</span>
              )}
              {draft.category && (
                <span className="text-xs text-gray-600 capitalize">{draft.category}</span>
              )}
            </div>
            <span
              className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-semibold border capitalize ${
                STATUS_STYLES[draft.status] || ''
              }`}
            >
              {draft.status}
            </span>
          </div>

          {/* Scheduled time display */}
          {draft.status === 'scheduled' && draft.scheduled_at && (
            <div className="text-xs text-purple-400 mb-2">
              ⏰ Scheduled for: {new Date(draft.scheduled_at).toLocaleString()}
            </div>
          )}

          {/* Article title */}
          {draft.article_title && (
            <p className="text-xs text-gray-500 mb-2 line-clamp-1">
              📰 {draft.article_title}
            </p>
          )}

          {/* Media preview + attach toggle */}
          {hasMedia && src && (
            <div className="mb-3 rounded-lg border border-gray-700 bg-gray-800/50 overflow-hidden">
              <div className="flex gap-3 p-2">
                <div className="w-20 h-20 shrink-0 rounded-md overflow-hidden bg-gray-900">
                  {draft.media_type === 'video' ? (
                    <video src={src} className="w-full h-full object-cover" muted playsInline controls />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={src} alt="Article media" className="w-full h-full object-cover" />
                  )}
                </div>
                <div className="flex-1 min-w-0 flex flex-col justify-center gap-1">
                  <p className="text-xs text-gray-400">
                    {draft.media_type === 'video' ? '🎬 Video' : '🖼️ Image'} available for this news
                  </p>
                  {(draft.status === 'draft' || draft.status === 'approved' || draft.status === 'scheduled') && (
                    <label className="flex items-center gap-2 text-xs text-gray-200 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={attachMedia}
                        disabled={loading}
                        onChange={(e) => handleToggleAttach(e.target.checked)}
                        className="w-3.5 h-3.5 rounded border-gray-600 bg-gray-800"
                      />
                      Attach to tweet when posting
                    </label>
                  )}
                  {draft.status === 'posted' && draft.attach_media && (
                    <span className="text-xs text-emerald-400">Attached on post</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tweet text - Rich editor */}
          {editing ? (
            <div className="mb-3">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={8}
                className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-3 text-sm text-white resize-y min-h-[120px] outline-none transition-colors font-mono"
                placeholder="Edit your post here (X Premium — long posts supported)..."
              />
              <div className="flex items-center justify-between mt-2">
                <div className="flex gap-2 text-xs flex-wrap">
                  <span className={isOverLimit ? 'text-red-400 font-bold' : 'text-gray-500'}>
                    {charCount.toLocaleString()} / {MAX_TWEET_LENGTH.toLocaleString()} chars
                  </span>
                  <span
                    className={
                      charRemaining < 500
                        ? 'text-yellow-400'
                        : charCount > 280
                        ? 'text-sky-400'
                        : 'text-gray-500'
                    }
                  >
                    {charRemaining.toLocaleString()} remaining
                    {charCount > 280 ? ' · Premium length' : ''}
                  </span>
                </div>
                {isOverLimit && (
                  <span className="text-red-400 text-xs font-bold">
                    ⚠️ Exceeds {MAX_TWEET_LENGTH.toLocaleString()} chars
                  </span>
                )}
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-200 mb-3 leading-relaxed break-words whitespace-pre-wrap max-h-64 overflow-y-auto">
                {draft.tweet_text}
              </p>
              {draft.tweet_text.length > 280 && (
                <p className="text-[10px] text-sky-500 mb-2">
                  Premium length · {draft.tweet_text.length.toLocaleString()} chars
                </p>
              )}
            </>
          )}

          {/* Post result */}
          {postResult && (
            <p className="text-xs text-blue-400 mb-2 break-all">{postResult}</p>
          )}

          {/* Actions */}
          {draft.status === 'draft' && (
            <div className="flex gap-2 flex-wrap">
              {editing ? (
                <>
                  <button
                    onClick={() => setShowPreview(true)}
                    className="text-xs px-3 py-1.5 bg-indigo-800 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
                  >
                    👁 Preview
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isOverLimit || loading}
                    className="text-xs px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                  >
                    ✓ Save Changes
                  </button>
                  <button
                    onClick={() => { setEditing(false); setEditText(draft.tweet_text); }}
                    className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                  >
                    ✕ Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setEditing(true)}
                    className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => setShowPreview(true)}
                    className="text-xs px-3 py-1.5 bg-indigo-800 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
                  >
                    👁 Preview
                  </button>
                  <button
                    onClick={() => handleAction('approve')}
                    disabled={loading}
                    className="text-xs px-3 py-1.5 bg-green-800 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                  >
                    ✓ Approve
                  </button>
                  <button
                    onClick={() => handleAction('reject')}
                    disabled={loading}
                    className="text-xs px-3 py-1.5 bg-red-900 hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                  >
                    ✗ Reject
                  </button>
                  <button
                    onClick={() => setShowScheduleModal(true)}
                    disabled={loading}
                    className="text-xs px-3 py-1.5 bg-purple-800 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                  >
                    📅 Schedule
                  </button>
                  <button
                    onClick={handleBrowserPost}
                    disabled={loading}
                    className="text-xs px-3 py-1.5 bg-sky-800 hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                    title="Opens X, fills the tweet; you click Post"
                  >
                    🌐 Open in browser
                  </button>
                </>
              )}
            </div>
          )}

          {(draft.status === 'scheduled' || draft.status === 'posted') && (
            <div className="flex gap-2 flex-wrap mb-0">
              <button
                onClick={() => setShowPreview(true)}
                className="text-xs px-3 py-1.5 bg-indigo-800 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
              >
                👁 Preview
              </button>
            </div>
          )}

          {draft.status === 'approved' && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setShowPreview(true)}
                className="text-xs px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors"
              >
                👁 Preview
              </button>
              <button
                onClick={handleBrowserPost}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                title="Opens X, fills the tweet; you click Post"
              >
                {loading ? '⏳ Opening…' : '🌐 Open in browser & post'}
              </button>
              <button
                onClick={handleMarkPosted}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-emerald-800 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                ✓ Mark as posted
              </button>
              <button
                onClick={() => handleAction('post')}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-300 rounded-lg font-medium transition-colors"
                title="Uses paid Twitter API if configured"
              >
                API post
              </button>
              <button
                onClick={() => setShowScheduleModal(true)}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-purple-800 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                📅 Schedule Instead
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Schedule Modal */}
      <ScheduleModal
        isOpen={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        onSchedule={handleSchedule}
        loading={loading}
      />

      {/* Live-style tweet preview */}
      <TweetPreviewModal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        tweetText={editing ? editText : draft.tweet_text}
        articleUrl={draft.article_url}
        mediaSrc={src}
        mediaType={draft.media_type}
        attachMedia={attachMedia}
        source={draft.source}
      />
    </div>
  );
}
