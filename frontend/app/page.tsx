'use client';

import { useState, useEffect, useCallback } from 'react';
import { NewsArticle, TweetDraft, Stats } from './types';
import NewsFeed from './components/NewsFeed';
import TweetCard from './components/TweetCard';
import SourceFilter from './components/SourceFilter';

const API_BASE = 'http://localhost:8000';
const TWEET_TABS = ['draft', 'approved', 'posted', 'rejected'] as const;

export default function Home() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [drafts, setDrafts] = useState<TweetDraft[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [tweetTab, setTweetTab] = useState<string>('draft');
  const [fetchingNews, setFetchingNews] = useState(false);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [message, setMessage] = useState('');
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

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

  const loadArticles = useCallback(async (category = 'all') => {
    try {
      const url =
        category === 'all'
          ? `${API_BASE}/api/news/`
          : `${API_BASE}/api/news/?category=${category}`;
      const res = await fetch(url);
      if (res.ok) setArticles(await res.json());
    } catch {
      /* backend offline */
    }
  }, []);

  const loadDrafts = useCallback(async (status: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/tweets/?status=${status}`);
      if (res.ok) setDrafts(await res.json());
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
        showMessage('Tweet draft generated!');
        if (tweetTab === 'draft') await loadDrafts('draft');
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
  };

  const handleDraftUpdate = async () => {
    await loadDrafts(tweetTab);
    await loadStats();
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
          <button
            onClick={handleFetchNews}
            disabled={fetchingNews}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          >
            {fetchingNews ? '⏳ Fetching...' : '🔄 Fetch Latest News'}
          </button>
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

      {/* Main Layout */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: News Feed (3/5) */}
          <div className="lg:col-span-3">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-200">
                News Articles
                <span className="ml-2 text-sm text-gray-500 font-normal">({articles.length})</span>
              </h2>
              <SourceFilter selected={categoryFilter} onChange={handleCategoryChange} />
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

            <div className="space-y-3 max-h-[calc(100vh-230px)] overflow-y-auto">
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
