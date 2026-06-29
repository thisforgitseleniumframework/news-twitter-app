'use client';

import { useState } from 'react';
import { TweetDraft } from '../types';

interface Props {
  draft: TweetDraft;
  onUpdate: () => void;
  apiBase: string;
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-yellow-950 text-yellow-400 border-yellow-800',
  approved: 'bg-green-950 text-green-400 border-green-800',
  posted: 'bg-blue-950 text-blue-400 border-blue-800',
  rejected: 'bg-red-950 text-red-500 border-red-900',
};

export default function TweetCard({ draft, onUpdate, apiBase }: Props) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(draft.tweet_text);
  const [loading, setLoading] = useState(false);
  const [postResult, setPostResult] = useState<string>('');

  const charCount = editText.length;
  const isOverLimit = charCount > 280;

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

  const handleAction = async (action: 'approve' | 'reject' | 'post') => {
    setLoading(true);
    setPostResult('');
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/${action}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (action === 'post') {
        if (data.success) {
          setPostResult(`Posted! View: ${data.tweet_url}`);
        } else {
          setPostResult(`Error: ${data.error}`);
        }
      }
      onUpdate();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors">
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

      {/* Article title */}
      {draft.article_title && (
        <p className="text-xs text-gray-500 mb-2 line-clamp-1">
          📰 {draft.article_title}
        </p>
      )}

      {/* Tweet text */}
      {editing ? (
        <div className="mb-3">
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-2.5 text-sm text-white resize-none outline-none transition-colors"
          />
          <div className={`text-right text-xs mt-1 font-mono ${isOverLimit ? 'text-red-400' : 'text-gray-500'}`}>
            {charCount} / 280
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-200 mb-3 leading-relaxed">{draft.tweet_text}</p>
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
                onClick={handleSave}
                disabled={isOverLimit || loading}
                className="text-xs px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
              >
                Save
              </button>
              <button
                onClick={() => { setEditing(false); setEditText(draft.tweet_text); }}
                className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
              >
                Cancel
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
                onClick={() => handleAction('approve')}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-green-800 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
              >
                ✓ Approve
              </button>
              <button
                onClick={() => handleAction('reject')}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-red-900 hover:bg-red-800 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
              >
                ✗ Reject
              </button>
            </>
          )}
        </div>
      )}

      {draft.status === 'approved' && (
        <button
          onClick={() => handleAction('post')}
          disabled={loading}
          className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
        >
          {loading ? 'Posting...' : '𝕏 Post to Twitter'}
        </button>
      )}

      {draft.status === 'posted' && draft.posted_at && (
        <p className="text-xs text-gray-600 mt-1">
          Posted {new Date(draft.posted_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
