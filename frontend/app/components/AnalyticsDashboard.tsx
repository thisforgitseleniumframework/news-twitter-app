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
  const [revenueGuide, setRevenueGuide] = useState<{
    program?: string;
    note?: string;
    account_eligibility?: Array<{ id?: string; label: string; detail?: string; why?: string } | string>;
    content_rules?: string[];
  } | null>(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [analyticsRes, peakRes, categoryRes, guideRes] = await Promise.all([
        fetch(`${apiBase}/api/tweets/analytics/overview`),
        fetch(`${apiBase}/api/tweets/analytics/peak-times`),
        fetch(`${apiBase}/api/tweets/analytics/category-stats`),
        fetch(`${apiBase}/api/tweets/revenue-guide`),
      ]);

      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (peakRes.ok) setPeakTimes(await peakRes.json());
      if (categoryRes.ok) setCategoryStats(await categoryRes.json());
      if (guideRes.ok) setRevenueGuide(await guideRes.json());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-gray-400 text-center py-10 text-sm animate-pulse">
        Loading analytics…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button type="button" onClick={fetchAnalytics} className="btn-ghost !text-xs">
        Refresh analytics
      </button>

      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="kpi-card text-center">
            <div className="text-4xl font-bold text-emerald-400 mb-2 tabular-nums">
              {analytics.success_rate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">Posting success rate</div>
            <div className="text-xs text-gray-600 mt-2">
              {analytics.total_posted} posted · {analytics.total_rejected} rejected
            </div>
          </div>

          <div className="kpi-card text-center">
            <div className="text-4xl font-bold text-sky-400 mb-2 tabular-nums">
              {analytics.total_posted}
            </div>
            <div className="text-sm text-gray-400">Successfully posted</div>
          </div>

          <div className="kpi-card text-center">
            <div className="text-4xl font-bold text-red-400 mb-2 tabular-nums">
              {analytics.total_rejected}
            </div>
            <div className="text-sm text-gray-400">Rejected tweets</div>
          </div>
        </div>
      )}

      {analytics && analytics.top_sources.length > 0 && (
        <div className="app-card-static p-5">
          <h3 className="section-title mb-4">Top performing sources</h3>
          <div className="space-y-3">
            {analytics.top_sources.map((source, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-xl bg-gray-800/60 border border-gray-800"
              >
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

      {/* X Creator Revenue — light guide */}
      {revenueGuide && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-1">
            {revenueGuide.program || 'X Creator Revenue Sharing'}
          </h3>
          {revenueGuide.note && (
            <p className="text-xs text-gray-500 mb-4">{revenueGuide.note}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-400 mb-2 font-medium">Account eligibility</div>
              <ul className="space-y-1.5 text-gray-300 list-disc pl-4">
                {(revenueGuide.account_eligibility || []).map((item, i) => (
                  <li key={typeof item === 'string' ? i : item.id || i}>
                    {typeof item === 'string'
                      ? item
                      : (
                        <>
                          <span className="text-gray-200">{item.label}</span>
                          {(item.why || item.detail) && (
                            <span className="text-gray-500"> — {item.why || item.detail}</span>
                          )}
                        </>
                      )}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-gray-400 mb-2 font-medium">Content rules (this app scores)</div>
              <ul className="space-y-1.5 text-gray-300 list-disc pl-4">
                {(revenueGuide.content_rules || []).map((rule, i) => (
                  <li key={i}>{rule}</li>
                ))}
              </ul>
            </div>
          </div>
          <p className="text-xs text-gray-600 mt-4">
            Draft cards show an &quot;X Revenue fit&quot; badge (score + grade). Expand it for tips after generate or edit.
          </p>
        </div>
      )}

    </div>
  );
}
