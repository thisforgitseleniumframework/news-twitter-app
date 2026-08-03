'use client';

import { useState, useEffect } from 'react';

interface AnalyticsData {
  success_rate: number;
  total_posted: number;
  total_rejected: number;
  top_sources: Array<{
    source: string;
    total: number;
    posted: number;
    success_rate: number;
  }>;
}

interface PeakHours {
  peak_hours: Array<{
    hour: string;
    count: number;
  }>;
  recommendation: string;
}

interface CategoryStats {
  india: {
    total: number;
    posted: number;
    success_rate: number;
  };
  global: {
    total: number;
    posted: number;
    success_rate: number;
  };
}

interface Props {
  apiBase: string;
}

export default function AnalyticsDashboard({ apiBase }: Props) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [peakTimes, setPeakTimes] = useState<PeakHours | null>(null);
  const [categoryStats, setCategoryStats] = useState<CategoryStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [analyticsRes, peakRes, categoryRes] = await Promise.all([
        fetch(`${apiBase}/api/tweets/analytics/overview`),
        fetch(`${apiBase}/api/tweets/analytics/peak-times`),
        fetch(`${apiBase}/api/tweets/analytics/category-stats`),
      ]);

      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (peakRes.ok) setPeakTimes(await peakRes.json());
      if (categoryRes.ok) setCategoryStats(await categoryRes.json());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-gray-400 text-center py-8">⏳ Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Refresh Button */}
      <button
        onClick={fetchAnalytics}
        className="text-xs px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
      >
        🔄 Refresh Analytics
      </button>

      {/* Success Rate & Overview */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
            <div className="text-4xl font-bold text-green-400 mb-2">
              {analytics.success_rate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">Posting Success Rate</div>
            <div className="text-xs text-gray-600 mt-2">
              {analytics.total_posted} posted, {analytics.total_rejected} rejected
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
            <div className="text-4xl font-bold text-blue-400 mb-2">{analytics.total_posted}</div>
            <div className="text-sm text-gray-400">Successfully Posted</div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
            <div className="text-4xl font-bold text-red-400 mb-2">{analytics.total_rejected}</div>
            <div className="text-sm text-gray-400">Rejected Tweets</div>
          </div>
        </div>
      )}

      {/* Top Performing Sources */}
      {analytics && analytics.top_sources.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">📊 Top Performing Sources</h3>
          <div className="space-y-3">
            {analytics.top_sources.map((source, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <div className="font-medium text-white">{source.source}</div>
                  <div className="text-xs text-gray-400">
                    {source.posted} of {source.total} posted
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-400">
                    {source.success_rate.toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Peak Posting Times */}
      {peakTimes && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">🕐 Peak Posting Times</h3>
          <div className="mb-4 p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
            <div className="text-sm text-blue-300">{peakTimes.recommendation}</div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {peakTimes.peak_hours.map((hour, idx) => (
              <div key={idx} className="bg-gray-800 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-yellow-400">{hour.hour}</div>
                <div className="text-xs text-gray-400">{hour.count} tweets</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category Performance (general + sports with activity) */}
      {categoryStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(categoryStats).map(([category, stats]) => {
            const s = stats as {
              total: number;
              posted: number;
              success_rate: number;
              label?: string;
            };
            return (
              <div key={category} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4">
                  {s.label || category}
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Tweets:</span>
                    <span className="text-white font-bold">{s.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Posted:</span>
                    <span className="text-green-400 font-bold">{s.posted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Success Rate:</span>
                    <span className="text-blue-400 font-bold">{s.success_rate.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
