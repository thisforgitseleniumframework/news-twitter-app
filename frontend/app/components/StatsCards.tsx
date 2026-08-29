'use client';

import { Stats } from '../types';

interface Props {
  stats: Stats;
  onSelectTab?: (tab: string) => void;
}

const CARDS: Array<{
  key: keyof Stats | 'scheduled';
  label: string;
  color: string;
  ring: string;
  tab?: string;
  icon: string;
}> = [
  {
    key: 'total_articles',
    label: 'Articles',
    color: 'text-sky-400',
    ring: 'from-sky-500/20 to-transparent',
    icon: '📰',
  },
  {
    key: 'draft_tweets',
    label: 'Drafts',
    color: 'text-amber-400',
    ring: 'from-amber-500/20 to-transparent',
    tab: 'draft',
    icon: '✏️',
  },
  {
    key: 'scheduled_tweets',
    label: 'Scheduled',
    color: 'text-purple-400',
    ring: 'from-purple-500/20 to-transparent',
    tab: 'scheduled',
    icon: '📅',
  },
  {
    key: 'approved_tweets',
    label: 'Approved',
    color: 'text-emerald-400',
    ring: 'from-emerald-500/20 to-transparent',
    tab: 'approved',
    icon: '✓',
  },
  {
    key: 'posted_tweets',
    label: 'Posted',
    color: 'text-blue-400',
    ring: 'from-blue-500/20 to-transparent',
    tab: 'posted',
    icon: '𝕏',
  },
  {
    key: 'rejected_tweets',
    label: 'Rejected',
    color: 'text-red-400',
    ring: 'from-red-500/20 to-transparent',
    tab: 'rejected',
    icon: '✕',
  },
];

export default function StatsCards({ stats, onSelectTab }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {CARDS.map((c) => {
        const value = stats[c.key as keyof Stats] ?? 0;
        const clickable = Boolean(c.tab && onSelectTab);
        const Comp = clickable ? 'button' : 'div';
        return (
          <Comp
            key={c.key}
            type={clickable ? 'button' : undefined}
            onClick={clickable ? () => onSelectTab?.(c.tab!) : undefined}
            className={`kpi-card text-left relative overflow-hidden ${
              clickable ? 'cursor-pointer hover:shadow-glow' : ''
            }`}
          >
            <div
              className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${c.ring} opacity-80`}
            />
            <div className="relative">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
                  {c.label}
                </span>
                <span className="text-sm opacity-80">{c.icon}</span>
              </div>
              <div className={`text-2xl font-bold tabular-nums tracking-tight ${c.color}`}>
                {Number(value).toLocaleString()}
              </div>
            </div>
          </Comp>
        );
      })}
    </div>
  );
}
