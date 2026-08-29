'use client';

import { useState, useEffect } from 'react';
import { TweetDraft } from '../types';
import ScheduleModal from './ScheduleModal';
import TweetPreviewModal from './TweetPreviewModal';

interface Props {
  draft: TweetDraft;
  onUpdate: () => void;
  /** Called after a successful schedule so parent can switch to the Scheduled tab */
  onScheduled?: () => void;
  apiBase: string;
  selected?: boolean;
  onSelectChange?: (selected: boolean) => void;
  showCheckbox?: boolean;
}

/** Single-post limits (must match backend config defaults: 250–500 words). */
const MAX_TWEET_LENGTH = 3500;
const MIN_TWEET_LENGTH = 1250;
const MIN_TWEET_WORDS = 250;
const MAX_TWEET_WORDS = 500;

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

export default function TweetCard({
  draft,
  onUpdate,
  onScheduled,
  apiBase,
  selected = false,
  onSelectChange,
  showCheckbox = false,
}: Props) {
  const isThread = Boolean(draft.is_thread && draft.thread_parts && draft.thread_parts.length >= 2);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(draft.tweet_text);
  const [editParts, setEditParts] = useState<string[]>(
    draft.thread_parts && draft.thread_parts.length >= 2 ? [...draft.thread_parts] : []
  );
  const [loading, setLoading] = useState(false);
  const [postResult, setPostResult] = useState<string>('');
  const [remainingParts, setRemainingParts] = useState<string[] | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showRevenueTips, setShowRevenueTips] = useState(false);
  const [showRulebook, setShowRulebook] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [attachMedia, setAttachMedia] = useState(Boolean(draft.attach_media && draft.media_path));

  useEffect(() => {
    setAttachMedia(Boolean(draft.attach_media && draft.media_path));
    setEditText(draft.tweet_text);
    setEditParts(
      draft.thread_parts && draft.thread_parts.length >= 2 ? [...draft.thread_parts] : []
    );
    setRemainingParts(null);
  }, [draft.id, draft.attach_media, draft.media_path, draft.tweet_text, draft.thread_parts]);

  const threadPartsForView =
    isThread && draft.thread_parts ? draft.thread_parts : null;
  const partOverLimit =
    isThread && editing
      ? editParts.some((p) => p.length > MAX_TWEET_LENGTH)
      : false;
  const charCount = isThread && editing
    ? editParts.reduce((s, p) => s + p.length, 0)
    : editText.length;
  const wordsCount = (editText || '').trim()
    ? ((editText.trim().match(/\b[\w']+\b/g) || []) as string[]).length
    : 0;
  const isOverLimit = isThread
    ? partOverLimit
    : charCount > MAX_TWEET_LENGTH;
  const charRemaining = isThread
    ? null
    : MAX_TWEET_LENGTH - charCount;
  const src = mediaSrc(draft, apiBase);
  const hasMedia = Boolean(src && draft.media_path);

  const handleSave = async () => {
    setLoading(true);
    try {
      const body =
        isThread
          ? { thread_parts: editParts.map((p) => p.trim()).filter(Boolean) }
          : { tweet_text: editText };
      if (isThread && (body as { thread_parts: string[] }).thread_parts.length < 2) {
        setPostResult('❌ Thread needs at least 2 parts');
        setLoading(false);
        return;
      }
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setEditing(false);
        onUpdate();
      } else {
        const err = await res.json().catch(() => ({}));
        setPostResult(`❌ ${err.detail || 'Save failed'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUseAlternative = async () => {
    const alt = (draft.alternative_tweet || '').trim();
    if (!alt || isThread) return;
    setLoading(true);
    setPostResult('');
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tweet_text: alt }),
      });
      if (res.ok) {
        setEditText(alt);
        setPostResult('✅ Switched to alternative angle');
        onUpdate();
      } else {
        const err = await res.json().catch(() => ({}));
        setPostResult(`❌ ${err.detail || 'Could not apply alternative'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const updatePart = (index: number, value: string) => {
    setEditParts((prev) => prev.map((p, i) => (i === index ? value : p)));
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
          const threadNote =
            data.thread_count && data.thread_count > 1
              ? ` · ${data.thread_count}-tweet thread`
              : '';
          setPostResult(`Posted!${mediaNote}${threadNote} View: ${data.tweet_url}`);
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
    setRemainingParts(null);
    try {
      const res = await fetch(`${apiBase}/api/tweets/${draft.id}/post-browser`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attach_media: attachMedia }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (data.is_thread && Array.isArray(data.remaining_parts)) {
          setRemainingParts(data.remaining_parts);
          setPostResult(
            `🌐 ${data.message || `Opened tweet 1/${data.total_parts}. Post it, then reply with the parts below.`}`
          );
        } else {
          setPostResult(
            `🌐 ${data.message || 'Browser opened. Review and click Post on X, then Mark as posted.'}`
          );
        }
      } else {
        setPostResult(`❌ ${data.detail || data.error || 'Could not open browser'}`);
      }
    } catch {
      setPostResult('❌ Failed to reach backend for browser post');
    } finally {
      setLoading(false);
    }
  };

  const copyPart = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setPostResult(`📋 Copied ${label}`);
    } catch {
      setPostResult('❌ Could not copy — select the text manually');
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
    setPostResult('');
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
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setShowScheduleModal(false);
        setPostResult(
          data.message
            ? `✅ ${data.message}`
            : '✅ Tweet scheduled! Open the Scheduled tab to see it.'
        );
        // Parent should switch to "scheduled" tab — draft leaves "draft" list
        if (onScheduled) {
          onScheduled();
        } else {
          onUpdate();
        }
      } else {
        const detail = data.detail;
        const msg =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ')
            : data.message || `Schedule failed (${res.status})`;
        setPostResult(`❌ ${msg}`);
      }
    } catch {
      setPostResult('❌ Cannot reach backend. Is it running on port 8000?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`rounded-2xl border p-4 transition-all duration-200 ${
        selected
          ? 'border-sky-500/70 bg-sky-950/20 shadow-glow'
          : 'border-gray-800 bg-gray-900/90 hover:border-gray-600 hover:bg-gray-900'
      }`}
    >
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

        {/* X-style avatar */}
        <div className="shrink-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-blue-600 text-sm font-bold text-white shadow-sm">
            N
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* X-style header */}
          <div className="flex items-start justify-between gap-2 mb-1.5">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-sm font-bold text-gray-50">NewsPost</span>
                <span className="text-xs text-gray-500">@newspost</span>
                <span className="text-xs text-gray-600">·</span>
                <span className="text-xs text-gray-500">
                  {draft.created_at
                    ? new Date(draft.created_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                      })
                    : ''}
                </span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-gray-500">
                {draft.source && <span className="truncate">{draft.source}</span>}
                {draft.category && (
                  <>
                    <span>·</span>
                    <span className="capitalize">{draft.category.replace(/_/g, ' ')}</span>

                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {isThread && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold border border-violet-700 bg-violet-950 text-violet-300">
                  🧵 Thread · {draft.thread_parts?.length || 0}
                </span>
              )}
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border capitalize ${
                  STATUS_STYLES[draft.status] || ''
                }`}
              >
                {draft.status}
              </span>
            </div>
          </div>

          {(draft.revenue_score != null || draft.revenue) && (
            <div className="mt-1 mb-2">
              <button
                type="button"
                onClick={() => setShowRevenueTips((v) => !v)}
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                  (draft.revenue_grade || draft.revenue?.grade || '').startsWith('A')
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : (draft.revenue_grade || draft.revenue?.grade || '') === 'B'
                    ? 'bg-sky-50 text-sky-800 border-sky-200'
                    : (draft.revenue_grade || draft.revenue?.grade || '') === 'C'
                    ? 'bg-amber-50 text-amber-900 border-amber-200'
                    : 'bg-slate-50 text-slate-700 border-slate-200'
                }`}
                title="X Creator Revenue Sharing content fit"
              >
                <span>X Revenue fit</span>
                <span className="font-semibold">
                  {draft.revenue?.score ?? draft.revenue_score ?? '—'}
                </span>
                <span className="opacity-80">
                  {draft.revenue?.grade ?? draft.revenue_grade ?? ''}
                </span>
                <span className="opacity-60">{showRevenueTips ? '▾' : '▸'}</span>
              </button>
              {showRevenueTips && (
                <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700 space-y-1">
                  {draft.revenue?.label && (
                    <p className="font-medium text-slate-800">{draft.revenue.label}</p>
                  )}
                  <ul className="list-disc pl-4 space-y-0.5">
                    {(draft.revenue?.tips?.length
                      ? draft.revenue.tips
                      : ['Edit the post, then save — tips refresh from the scorer.']
                    ).map((tip, i) => (
                      <li key={i}>{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Master Rulebook §17 — Hidden Story / Alternative */}
          {draft.rulebook && (draft.hidden_story || draft.alternative_tweet) && (
            <div className="mt-1 mb-2">
              <button
                type="button"
                onClick={() => setShowRulebook((v) => !v)}
                className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border border-amber-800/70 bg-amber-950/40 text-amber-200 transition-colors hover:bg-amber-950/70"
                title="Master Rulebook analysis for this draft"
              >
                <span>📖 Rulebook</span>
                {draft.rulebook_mode && (
                  <span className="opacity-70 font-normal">
                    · {draft.rulebook_mode === 'gemini_rulebook' ? 'AI' : 'local'}
                  </span>
                )}
                <span className="opacity-60">{showRulebook ? '▾' : '▸'}</span>
              </button>
              {showRulebook && (
                <div className="mt-2 rounded-lg border border-amber-900/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-100/90 space-y-2">
                  {draft.hidden_story && (
                    <div>
                      <p className="font-semibold text-amber-200 mb-0.5">Hidden story</p>
                      <p className="text-amber-100/80 leading-relaxed">{draft.hidden_story}</p>
                    </div>
                  )}
                  {Array.isArray(draft.verified_context) && draft.verified_context.length > 0 && (
                    <div>
                      <p className="font-semibold text-amber-200 mb-0.5">Verified context</p>
                      <ul className="list-disc pl-4 space-y-0.5 text-amber-100/75">
                        {draft.verified_context.slice(0, 5).map((fact, i) => (
                          <li key={i}>{fact}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {Array.isArray(draft.uncertain) && draft.uncertain.length > 0 && (
                    <div>
                      <p className="font-semibold text-amber-200/90 mb-0.5">Uncertain</p>
                      <ul className="list-disc pl-4 space-y-0.5 text-amber-100/60">
                        {draft.uncertain.slice(0, 3).map((u, i) => (
                          <li key={i}>{u}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {draft.alternative_tweet &&
                    draft.alternative_tweet.trim() !== (draft.tweet_text || '').trim() &&
                    (draft.status === 'draft' || draft.status === 'approved') && (
                      <button
                        type="button"
                        disabled={loading || isThread}
                        onClick={handleUseAlternative}
                        className="mt-1 inline-flex items-center gap-1 rounded-md border border-amber-700/60 bg-amber-900/40 px-2.5 py-1 text-[11px] font-medium text-amber-100 hover:bg-amber-800/50 disabled:opacity-50"
                      >
                        Use alternative angle
                      </button>
                    )}
                </div>
              )}
            </div>
          )}

          {/* Scheduled time display */}
          {draft.status === 'scheduled' && draft.scheduled_at && (
            <div className="text-xs text-purple-300 mb-2 space-y-0.5">
              <div>
                ⏰ Scheduled for:{' '}
                <strong>
                  {new Date(draft.scheduled_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </strong>
              </div>
              {draft.twitter_post_id?.startsWith('browser-due') ? (
                <div className="text-amber-400">
                  Browser compose was opened — click Post on X, then{' '}
                  <strong>Mark as posted</strong>.
                </div>
              ) : new Date(draft.scheduled_at).getTime() <= Date.now() ? (
                <div className="text-amber-400">
                  Due now — backend will open the browser (or post via API) within ~1 min.
                </div>
              ) : (
                <div className="text-purple-400/80">
                  Waiting until the scheduled time (checked every minute).
                </div>
              )}
            </div>
          )}

          {/* Article title */}
          {draft.article_title && (
            <p className="text-[11px] text-gray-500 mb-2 line-clamp-1 border-l-2 border-gray-700 pl-2">
              {draft.article_title}
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

          {/* Tweet / thread body */}
          {editing ? (
            <div className="mb-3 space-y-3">
              {isThread ? (
                editParts.map((part, i) => (
                  <div key={i} className="rounded-lg border border-violet-900/50 bg-gray-800/40 p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-semibold text-violet-300">
                        {i + 1}/{editParts.length}
                      </span>
                      <span
                        className={`text-[10px] ${
                          part.length > MAX_TWEET_LENGTH ? 'text-red-400 font-bold' : 'text-gray-500'
                        }`}
                      >
                        {part.length.toLocaleString()} chars
                      </span>
                    </div>
                    <textarea
                      value={part}
                      onChange={(e) => updatePart(i, e.target.value)}
                      rows={4}
                      className="w-full bg-gray-800 border border-gray-700 focus:border-violet-500 rounded-lg p-2.5 text-sm text-white resize-y min-h-[80px] outline-none transition-colors font-mono"
                      placeholder={`Tweet ${i + 1}...`}
                    />
                  </div>
                ))
              ) : (
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={8}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-3 text-sm text-white resize-y min-h-[120px] outline-none transition-colors font-mono"
                  placeholder={`Edit post (${MIN_TWEET_WORDS}–${MAX_TWEET_WORDS} words)...`}
                />
              )}
              <div className="flex items-center justify-between">
                <div className="flex gap-2 text-xs flex-wrap">
                  {isThread ? (
                    <span className={isOverLimit ? 'text-red-400 font-bold' : 'text-gray-500'}>
                      {editParts.length} tweets · {charCount.toLocaleString()} chars total
                    </span>
                  ) : (
                    <>
                      <span className={isOverLimit ? 'text-red-400 font-bold' : 'text-gray-500'}>
                        {wordsCount.toLocaleString()} words · {charCount.toLocaleString()} /{' '}
                        {MAX_TWEET_LENGTH.toLocaleString()} chars
                      </span>
                      {charRemaining !== null && (
                        <span
                          className={
                            wordsCount < MIN_TWEET_WORDS
                              ? 'text-yellow-400'
                              : charRemaining < 200
                              ? 'text-amber-400'
                              : 'text-sky-400'
                          }
                        >
                          {wordsCount < MIN_TWEET_WORDS
                            ? `aim ${MIN_TWEET_WORDS}–${MAX_TWEET_WORDS} words`
                            : wordsCount > MAX_TWEET_WORDS
                            ? `over ${MAX_TWEET_WORDS} word max`
                            : `${charRemaining.toLocaleString()} chars left`}
                        </span>
                      )}
                    </>
                  )}
                </div>
                {isOverLimit && (
                  <span className="text-red-400 text-xs font-bold">
                    ⚠️ Exceeds {MAX_TWEET_LENGTH.toLocaleString()} chars
                  </span>
                )}
                {!isThread && !isOverLimit && wordsCount > 0 && wordsCount < MIN_TWEET_WORDS && (
                  <span className="text-yellow-400 text-xs">
                    Under {MIN_TWEET_WORDS} words — add real facts from sources
                  </span>
                )}
                {!isThread && wordsCount > MAX_TWEET_WORDS && (
                  <span className="text-amber-400 text-xs">
                    Over {MAX_TWEET_WORDS} words — trim to stay in range
                  </span>
                )}
              </div>
            </div>
          ) : threadPartsForView ? (
            <div className="mb-3 space-y-2 max-h-80 overflow-y-auto">
              {threadPartsForView.map((part, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-violet-900/40 bg-violet-950/20 p-2.5"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold text-violet-400">
                      {i + 1}/{threadPartsForView.length}
                    </span>
                    <button
                      type="button"
                      onClick={() => copyPart(part, `tweet ${i + 1}`)}
                      className="text-[10px] text-gray-500 hover:text-sky-400"
                      title="Copy this tweet"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="text-sm text-gray-200 leading-relaxed break-words whitespace-pre-wrap">
                    {part}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-200 mb-3 leading-relaxed break-words whitespace-pre-wrap max-h-64 overflow-y-auto">
                {draft.tweet_text}
              </p>
              <p className="text-[10px] text-sky-500 mb-2">
                {(
                  (draft.tweet_text || '').trim().match(/\b[\w']+\b/g) || []
                ).length.toLocaleString()}{' '}
                words · {draft.tweet_text.length.toLocaleString()} chars
                {` · target ${MIN_TWEET_WORDS}–${MAX_TWEET_WORDS} words`}
              </p>
            </>
          )}

          {/* Post result */}
          {postResult && (
            <p className="text-xs text-blue-400 mb-2 break-all">{postResult}</p>
          )}

          {/* Remaining thread parts after browser opens tweet 1 */}
          {remainingParts && remainingParts.length > 0 && (
            <div className="mb-3 rounded-xl border border-amber-800/50 bg-amber-950/20 p-3 space-y-2">
              <p className="text-xs text-amber-300 font-semibold">
                Reply on X with these remaining tweets (in order):
              </p>
              {remainingParts.map((part, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <span className="text-[10px] text-amber-500 font-bold shrink-0 pt-0.5">
                    {i + 2}
                  </span>
                  <p className="text-xs text-gray-300 flex-1 whitespace-pre-wrap break-words">
                    {part}
                  </p>
                  <button
                    type="button"
                    onClick={() => copyPart(part, `tweet ${i + 2}`)}
                    className="text-[10px] px-2 py-1 rounded bg-amber-900/50 hover:bg-amber-800 text-amber-200 shrink-0"
                  >
                    Copy
                  </button>
                </div>
              ))}
            </div>
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
                    onClick={() => {
                      setEditing(false);
                      setEditText(draft.tweet_text);
                      setEditParts(
                        draft.thread_parts && draft.thread_parts.length >= 2
                          ? [...draft.thread_parts]
                          : []
                      );
                    }}
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
        isThread={isThread}
        threadParts={editing && isThread ? editParts : draft.thread_parts}
      />
    </div>
  );
}
