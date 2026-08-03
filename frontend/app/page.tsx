'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { NewsArticle, TweetDraft, Stats } from './types';
import NewsFeed from './components/NewsFeed';
import TweetCard from './components/TweetCard';
import SourceFilter from './components/SourceFilter';
import AdvancedFilters, { FilterState } from './components/AdvancedFilters';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import ThemeToggle from './components/ThemeToggle';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';
const TWEET_TABS = ['draft', 'approved', 'posted', 'rejected', 'scheduled'] as const;

export default function Home() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [drafts, setDrafts] = useState<TweetDraft[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  /** priority = breaking first (default), recent = newest first, breaking = only high priority */
  const [newsSort, setNewsSort] = useState<'priority' | 'recent' | 'breaking'>('priority');
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

  const loadArticles = useCallback(async (category = 'all', sort = newsSort) => {
    try {
      let url = `${API_BASE}/api/news/?limit=200&sort=${sort}`;
      if (category !== 'all') url += `&category=${category}`;
      if (filters.keyword) url += `&keyword=${encodeURIComponent(filters.keyword)}`;
      if (filters.source) url += `&source=${encodeURIComponent(filters.source)}`;
      if (filters.days) url += `&days=${filters.days}`;
      if (filters.processed !== null) url += `&processed=${filters.processed}`;

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

  const handleGenerateTweet = async (articleId: number) => {
    setGeneratingId(articleId);
    try {
      const res = await fetch(`${API_BASE}/api/news/${articleId}/generate-tweet`, {
        method: 'POST',
      });
      if (res.ok) {
        showMessage('Tweet draft generated! You can tweet this news again anytime.');
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
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-xl font-bold tracking-tight">📰 NewsPost</h1>
              <p className="text-gray-500 text-xs">
                Global &amp; India news → AI tweets → Post to 𝕏
              </p>
            </div>
            {backendOnline === false && (
              <span className="text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-1 rounded-lg">
                ⚠ Backend offline
              </span>
            )}
            {backendOnline === true && (
              <span className="text-xs bg-green-950 text-green-500 border border-green-900 px-2 py-1 rounded-lg">
                ● Connected
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleFetchNews}
              disabled={fetchingNews}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
            >
              {fetchingNews ? '⏳ Fetching...' : '🔄 Fetch Latest News'}
            </button>
            <button
              onClick={() => setShowAnalytics(!showAnalytics)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                showAnalytics
                  ? 'bg-purple-600 hover:bg-purple-500 text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
            >
              📊 Analytics
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      {stats && (
        <div className="bg-gray-900 border-b border-gray-800 px-6 py-2.5">
          <div className="max-w-7xl mx-auto flex items-center gap-6 text-sm">
            <span className="text-gray-400">
              Articles: <strong className="text-white">{stats.total_articles}</strong>
            </span>
            <span className="text-gray-400">
              Drafts: <strong className="text-yellow-400">{stats.draft_tweets}</strong>
            </span>
            <span className="text-gray-400">
              Approved: <strong className="text-green-400">{stats.approved_tweets}</strong>
            </span>
            <span className="text-gray-400">
              Posted: <strong className="text-blue-400">{stats.posted_tweets}</strong>
            </span>
            <span className="text-gray-400">
              Rejected: <strong className="text-red-400">{stats.rejected_tweets}</strong>
            </span>
          </div>
        </div>
      )}

      {/* Notification bar */}
      {message && (
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-2">
          <p className="max-w-7xl mx-auto text-sm text-gray-300">{message}</p>
        </div>
      )}

      {/* Analytics Dashboard */}
      {showAnalytics && (
        <div className="max-w-7xl mx-auto px-6 py-6 border-b border-gray-800">
          <AnalyticsDashboard apiBase={API_BASE} />
        </div>
      )}

      {/* Main Layout */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Advanced Filters */}
        <div className="mb-6">
          <AdvancedFilters onFilterChange={(newFilters) => {
            setFilters(newFilters);
            loadArticles(categoryFilter);
          }} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: News Feed (3/5) */}
          <div className="lg:col-span-3">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <h2 className="font-semibold text-gray-200">
                News Articles
                <span className="ml-2 text-sm text-gray-500 font-normal">({articles.length})</span>
              </h2>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex rounded-lg overflow-hidden border border-gray-700 text-xs">
                  {(
                    [
                      { id: 'priority', label: '🔥 Priority' },
                      { id: 'breaking', label: '🚨 Breaking' },
                      { id: 'recent', label: '🕒 Latest' },
                    ] as const
                  ).map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => {
                        setNewsSort(opt.id);
                        loadArticles(categoryFilter, opt.id);
                      }}
                      className={`px-2.5 py-1 font-medium transition-colors ${
                        newsSort === opt.id
                          ? 'bg-red-700 text-white'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
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
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <h2 className="font-semibold text-gray-200">Tweets</h2>
              <div className="flex gap-1 ml-auto">
                {TWEET_TABS.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => handleTweetTabChange(tab)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                      tweetTab === tab
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-500 hover:bg-gray-700 hover:text-gray-300'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
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

            <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
              {drafts.length === 0 ? (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
                  <p className="text-gray-500 text-sm">No {tweetTab} tweets.</p>
                  {tweetTab === 'draft' && (
                    <p className="text-gray-600 text-xs mt-1">
                      Click &quot;✍️ Tweet&quot; on any article to generate a draft.
                    </p>
                  )}
                </div>
              ) : (
                drafts.map((draft) => (
                  <TweetCard
                    key={draft.id}
                    draft={draft}
                    onUpdate={handleDraftUpdate}
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
