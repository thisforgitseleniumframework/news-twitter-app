'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { NewsArticle, TweetDraft, Stats } from './types';
import NewsFeed from './components/NewsFeed';
import TweetCard from './components/TweetCard';
import SourceFilter from './components/SourceFilter';
import AdvancedFilters, { FilterState } from './components/AdvancedFilters';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import ThemeToggle from './components/ThemeToggle';
import TrendsBar from './components/TrendsBar';
import StatsCards from './components/StatsCards';
import Toast, { toastKindFromMessage } from './components/Toast';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';
const TWEET_TABS = ['draft', 'approved', 'posted', 'rejected', 'scheduled'] as const;

export default function Home() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [drafts, setDrafts] = useState<TweetDraft[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  /** priority = breaking first, recent = newest first (default), breaking = only high priority */
  const [newsSort, setNewsSort] = useState<'priority' | 'recent' | 'breaking'>('recent');
  const [tweetTab, setTweetTab] = useState<string>('draft');
  const [fetchingNews, setFetchingNews] = useState(false);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [message, setMessage] = useState('');
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  
  // Batch selection state
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);

  // Advanced filters
  const [filters, setFilters] = useState<FilterState>({
    keyword: '',
    source: '',
    days: null,
    processed: null,
  });

  // Analytics view toggle
  const [showAnalytics, setShowAnalytics] = useState(false);
  
  // WebSocket for real-time stats
  const wsRef = useRef<WebSocket | null>(null);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 5000);
  };

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) setStats(await res.json());
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket(`${WS_BASE}/api/tweets/ws/stats`);
        
        wsRef.current.onopen = () => {
          console.log('WebSocket connected');
          // Send initial ping to get stats
          wsRef.current?.send('ping');
          // Request stats every 5 seconds
          const interval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send('ping');
            }
          }, 5000);
          return () => clearInterval(interval);
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setStats(data);
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };
        
        wsRef.current.onerror = () => {
          console.log('WebSocket error, falling back to HTTP polling');
          // Fallback to HTTP polling
          loadStats();
        };
        
        wsRef.current.onclose = () => {
          console.log('WebSocket closed');
          // Retry connection after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };
      } catch (e) {
        console.log('WebSocket connection failed, using HTTP polling:', e);
        loadStats();
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [loadStats]);

  const loadArticles = useCallback(async (
    category = 'all',
    sort = newsSort,
    filterOverride?: Partial<FilterState>,
  ) => {
    try {
      const f = { ...filters, ...filterOverride };
      let url = `${API_BASE}/api/news/?limit=200&sort=${sort}`;
      if (category !== 'all') url += `&category=${category}`;
      if (f.keyword) url += `&keyword=${encodeURIComponent(f.keyword)}`;
      if (f.source) url += `&source=${encodeURIComponent(f.source)}`;
      if (f.days) url += `&days=${f.days}`;
      if (f.processed !== null && f.processed !== undefined) {
        url += `&processed=${f.processed}`;
      }

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setArticles(data.articles || data);
      }
    } catch {
      /* backend offline */
    }
  }, [filters, newsSort]);

  const loadDrafts = useCallback(async (status: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/tweets/?status=${status}`);
      if (res.ok) {
        const data = await res.json();
        setDrafts(Array.isArray(data) ? data : data.drafts || []);
      }
    } catch {
      /* backend offline */
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadArticles();
    loadDrafts('draft');
  }, [loadStats, loadArticles, loadDrafts]);

  const handleFetchNews = async () => {
    setFetchingNews(true);
    try {
      // Always pull general + all sports feeds so every category tab is populated
      const res = await fetch(`${API_BASE}/api/news/fetch?category=all`);
      const data = await res.json();
      showMessage(data.message);
      await loadArticles(categoryFilter);
      await loadStats();
    } catch {
      showMessage('Cannot reach backend. Make sure it is running on port 8000.');
    } finally {
      setFetchingNews(false);
    }
  };

  const handleGenerateTweet = async (
    articleId: number,
    format: 'auto' | 'single' | 'thread' = 'single'
  ) => {
    setGeneratingId(articleId);
    try {
      const qs = `?format=${format || 'single'}`;
      const res = await fetch(
        `${API_BASE}/api/news/${articleId}/generate-tweet${qs}`,
        { method: 'POST' }
      );
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        const isThread = data.is_thread || data.format === 'thread';
        const n = Array.isArray(data.thread_parts) ? data.thread_parts.length : 0;
        if (isThread) {
          showMessage(
            `Thread draft ready (${n || 3} tweets). Edit, approve, then post.`
          );
        } else if (data.rulebook && data.hidden_story) {
          const wc = data.word_count ? ` · ${data.word_count} words` : '';
          showMessage(
            `Rulebook draft ready${wc}. Hidden story: ${String(data.hidden_story).slice(0, 140)}…`
          );
        } else {
          showMessage('Tweet draft generated! You can tweet this news again anytime.');
        }
        setTweetTab('draft');
        await loadDrafts('draft');
        await loadStats();
        await loadArticles(categoryFilter);
      } else {
        const err = await res.json();
        showMessage(`Error: ${err.detail || 'Failed to generate tweet'}`);
      }
    } catch {
      showMessage('Error generating tweet. Check your GEMINI_API_KEY in .env');
    } finally {
      setGeneratingId(null);
    }
  };

  const handleCategoryChange = (category: string) => {
    setCategoryFilter(category);
    loadArticles(category);
  };

  const handleTweetTabChange = (tab: string) => {
    setTweetTab(tab);
    loadDrafts(tab);
    setSelectedIds(new Set()); // Clear selections when switching tabs
  };

  const handleDraftUpdate = async () => {
    await loadDrafts(tweetTab);
    await loadStats();
  };

  // Batch selection handlers
  const toggleSelection = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const selectAll = () => {
    if (selectedIds.size === drafts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(drafts.map(d => d.id)));
    }
  };

  const handleBatchAction = async (action: 'approve' | 'reject' | 'delete') => {
    if (selectedIds.size === 0) {
      showMessage('No tweets selected');
      return;
    }

    setBatchLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/tweets/batch/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ids: Array.from(selectedIds),
          action
        }),
      });

      if (res.ok) {
        const data = await res.json();
        showMessage(data.message);
        setSelectedIds(new Set());
        await loadDrafts(tweetTab);
        await loadStats();
      }
    } catch (err) {
      showMessage('Failed to perform batch action');
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-white">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 text-lg font-black text-white shadow-glow">
              N
            </div>
            <div className="min-w-0">
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white">
                NewsPost
              </h1>
              <p className="text-gray-500 text-[11px] sm:text-xs truncate">
                News → AI drafts → 𝕏
              </p>
            </div>
            {backendOnline === false && (
              <span className="hidden sm:inline-flex pill bg-red-950/80 text-red-400 border-red-800">
                <span className="h-1.5 w-1.5 rounded-full bg-red-400" /> Offline
              </span>
            )}
            {backendOnline === true && (
              <span className="hidden sm:inline-flex pill bg-emerald-950/60 text-emerald-400 border-emerald-900">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={handleFetchNews}
              disabled={fetchingNews}
              className="btn-primary disabled:bg-gray-700 disabled:text-gray-500"
            >
              {fetchingNews ? 'Fetching…' : 'Fetch news'}
            </button>
            <button
              type="button"
              onClick={() => setShowAnalytics(!showAnalytics)}
              className={`btn-ghost ${
                showAnalytics
                  ? '!bg-purple-600/20 !border-purple-500/50 !text-purple-200'
                  : ''
              }`}
            >
              Analytics
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* KPI cards */}
      {stats && (
        <div className="border-b border-gray-800/60 bg-gray-950/40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
            <StatsCards
              stats={stats}
              onSelectTab={(tab) => {
                setTweetTab(tab);
                loadDrafts(tab);
              }}
            />
          </div>
        </div>
      )}

      <Toast
        message={message}
        kind={toastKindFromMessage(message)}
        onClose={() => setMessage('')}
      />

      {/* Analytics Dashboard */}
      {showAnalytics && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 border-b border-gray-800/60">
          <div className="app-card-static p-5">
            <h2 className="section-title mb-4">Analytics</h2>
            <AnalyticsDashboard apiBase={API_BASE} />
          </div>
        </div>
      )}

      {/* Main Layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* X Trends → filter news by trending topic */}
        <TrendsBar
          selectedQuery={filters.keyword || null}
          onSelectTrend={(query, label) => {
            setFilters((prev) => ({ ...prev, keyword: query }));
            loadArticles(categoryFilter, newsSort, { keyword: query });
            showMessage(`Showing news matching X trend: ${label}`);
          }}
          onClear={() => {
            setFilters((prev) => ({ ...prev, keyword: '' }));
            loadArticles(categoryFilter, newsSort, { keyword: '' });
            showMessage('Cleared trend filter');
          }}
          onDraftsCreated={({ created, message }) => {
            showMessage(message || `Created ${created} trend draft(s)`);
            if (created > 0) {
              setTweetTab('draft');
              loadDrafts('draft');
              loadStats();
            }
          }}
        />

        {/* Advanced Filters */}
        <div className="mb-6">
          <AdvancedFilters onFilterChange={(newFilters) => {
            setFilters(newFilters);
            loadArticles(categoryFilter, newsSort, newFilters);
          }} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: News Feed (3/5) */}
          <div className="lg:col-span-3 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="section-title">
                News
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({articles.length})
                </span>
              </h2>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex rounded-xl overflow-hidden border border-gray-700/80 text-xs bg-gray-900/60">
                  {(
                    [
                      { id: 'priority', label: 'Priority' },
                      { id: 'breaking', label: 'Breaking' },
                      { id: 'recent', label: 'Latest' },
                    ] as const
                  ).map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => {
                        setNewsSort(opt.id);
                        loadArticles(categoryFilter, opt.id);
                      }}
                      className={`px-3 py-1.5 font-medium transition-colors ${
                        newsSort === opt.id
                          ? 'bg-sky-600 text-white'
                          : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                      }`}
                      title={
                        opt.id === 'priority'
                          ? 'Breaking & urgent first'
                          : opt.id === 'breaking'
                          ? 'Only high-priority stories'
                          : 'Newest fetch first'
                      }
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <SourceFilter selected={categoryFilter} onChange={handleCategoryChange} />
              </div>
            </div>
            <NewsFeed
              articles={articles}
              onGenerateTweet={handleGenerateTweet}
              generatingId={generatingId}
            />
          </div>

          {/* Right: Tweet Drafts (2/5) */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="section-title">Tweets</h2>
              <div className="flex gap-1 ml-auto flex-wrap justify-end">
                {TWEET_TABS.map((tab) => {
                  const count =
                    !stats
                      ? undefined
                      : tab === 'draft'
                      ? stats.draft_tweets
                      : tab === 'scheduled'
                      ? stats.scheduled_tweets
                      : tab === 'posted'
                      ? stats.posted_tweets
                      : tab === 'rejected'
                      ? stats.rejected_tweets
                      : tab === 'approved'
                      ? stats.approved_tweets
                      : undefined;
                  return (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => handleTweetTabChange(tab)}
                      className={`px-2.5 py-1 rounded-full text-[11px] font-semibold capitalize transition-colors border ${
                        tweetTab === tab
                          ? 'bg-sky-600 text-white border-sky-500'
                          : 'bg-gray-900/80 text-gray-500 border-gray-800 hover:border-gray-600 hover:text-gray-300'
                      }`}
                    >
                      {tab}
                      {typeof count === 'number' && count > 0 && (
                        <span className="ml-1 opacity-80">{count}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Batch mode controls */}
            {drafts.length > 0 && (
              <div className="mb-3 flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => setBatchMode(!batchMode)}
                  className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    batchMode
                      ? 'bg-purple-700 text-white'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {batchMode ? '✓ Batch ON' : '☐ Batch'}
                </button>

                {batchMode && (
                  <>
                    <button
                      onClick={selectAll}
                      className="text-xs px-2.5 py-1 bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg font-medium transition-colors"
                    >
                      {selectedIds.size === drafts.length ? '☑ All' : '☐ All'}
                    </button>

                    {selectedIds.size > 0 && (
                      <>
                        <span className="text-xs text-gray-400 ml-auto">
                          {selectedIds.size} selected
                        </span>

                        <button
                          onClick={() => handleBatchAction('approve')}
                          disabled={batchLoading}
                          className="text-xs px-2.5 py-1 bg-green-800 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                        >
                          ✓ Approve
                        </button>

                        <button
                          onClick={() => handleBatchAction('reject')}
                          disabled={batchLoading}
                          className="text-xs px-2.5 py-1 bg-red-900 hover:bg-red-800 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                        >
                          ✗ Reject
                        </button>

                        <button
                          onClick={() => handleBatchAction('delete')}
                          disabled={batchLoading}
                          className="text-xs px-2.5 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                        >
                          🗑 Delete
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            )}

            <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto scrollbar-thin pr-0.5">
              {drafts.length === 0 ? (
                <div className="app-card-static border-dashed p-10 text-center">
                  <p className="text-gray-400 text-sm font-medium">No {tweetTab} tweets</p>
                  {tweetTab === 'draft' && (
                    <p className="text-gray-600 text-xs mt-1.5">
                      Click <span className="text-sky-400">Tweet</span> on any article, or generate
                      from X trends.
                    </p>
                  )}
                </div>
              ) : (
                drafts.map((draft) => (
                  <TweetCard
                    key={draft.id}
                    draft={draft}
                    onUpdate={handleDraftUpdate}
                    onScheduled={() => {
                      showMessage('Tweet scheduled — switched to Scheduled tab');
                      setTweetTab('scheduled');
                      loadDrafts('scheduled');
                      loadStats();
                    }}
                    apiBase={API_BASE}
                    showCheckbox={batchMode}
                    selected={selectedIds.has(draft.id)}
                    onSelectChange={(selected) => {
                      if (selected) {
                        setSelectedIds(new Set([...Array.from(selectedIds), draft.id]));
                      } else {
                        const newSelected = new Set(selectedIds);
                        newSelected.delete(draft.id);
                        setSelectedIds(newSelected);
                      }
                    }}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
