'use client';

import { useEffect, useMemo, useState } from 'react';

interface ScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSchedule: (scheduledAt: string) => void;
  loading: boolean;
}

function pad(n: number) {
  return String(n).padStart(2, '0');
}

/** Local calendar date as YYYY-MM-DD */
function localDateString(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Local time as HH:mm */
function localTimeString(d = new Date()) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Build a Date in the user's local timezone from date + time inputs.
 * Avoids UTC shift bugs from toISOString() alone.
 */
function localDateTime(dateStr: string, timeStr: string): Date | null {
  if (!dateStr || !timeStr) return null;
  // time input may be "HH:mm" or "HH:mm:ss"
  const [y, m, day] = dateStr.split('-').map(Number);
  const [hh, mm, ss] = timeStr.split(':').map(Number);
  if (!y || !m || !day || Number.isNaN(hh) || Number.isNaN(mm)) return null;
  return new Date(y, m - 1, day, hh, mm || 0, ss || 0, 0);
}

/**
 * Naive local ISO (no Z / offset). Backend treats this as server-local time.
 * Matches how we store scheduled_at with datetime.now().
 */
function toLocalNaiveISO(d: Date): string {
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

function formatPreview(d: Date): string {
  return d.toLocaleString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function format24h(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ScheduleModal({
  isOpen,
  onClose,
  onSchedule,
  loading,
}: ScheduleModalProps) {
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('09:00');
  const [error, setError] = useState('');

  // Defaults when opening
  useEffect(() => {
    if (!isOpen) return;
    const now = new Date();
    // Suggest ~1 hour from now
    const soon = new Date(now.getTime() + 60 * 60 * 1000);
    setScheduledDate(localDateString(soon));
    setScheduledTime(localTimeString(soon));
    setError('');
  }, [isOpen]);

  const when = useMemo(
    () => localDateTime(scheduledDate, scheduledTime),
    [scheduledDate, scheduledTime]
  );

  const today = localDateString();
  const maxDate = localDateString(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000));

  if (!isOpen) return null;

  const handleSchedule = () => {
    setError('');
    if (!scheduledDate || !scheduledTime) {
      setError('Please select both date and time.');
      return;
    }
    const dt = localDateTime(scheduledDate, scheduledTime);
    if (!dt || Number.isNaN(dt.getTime())) {
      setError('Invalid date/time.');
      return;
    }
    if (dt.getTime() <= Date.now() + 30_000) {
      setError('Scheduled time must be at least ~30 seconds in the future.');
      return;
    }
    onSchedule(toLocalNaiveISO(dt));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-sm w-full shadow-xl">
        <h2 className="text-lg font-semibold text-white mb-4">📅 Schedule Tweet</h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400 block mb-2">Date</label>
            <input
              type="date"
              min={today}
              max={maxDate}
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-2 text-white outline-none"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-2">
              Time
              <span className="text-gray-500 font-normal">
                {' '}
                (your local time
                {when ? ` · ${format24h(when)}` : ''})
              </span>
            </label>
            <input
              type="time"
              value={scheduledTime}
              onChange={(e) => setScheduledTime(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-2 text-white outline-none"
            />
            <p className="text-[10px] text-gray-500 mt-1">
              Your browser may show AM/PM — that is normal. Value is your local clock.
            </p>
          </div>

          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-2">💡 Quick pick (local):</p>
            <div className="grid grid-cols-3 gap-2">
              {['08:00', '12:00', '18:00'].map((time) => (
                <button
                  key={time}
                  type="button"
                  onClick={() => setScheduledTime(time)}
                  className={`text-xs px-2 py-1 rounded transition-colors ${
                    scheduledTime === time || scheduledTime.startsWith(time)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 hover:bg-blue-600 text-gray-300 hover:text-white'
                  }`}
                >
                  {time}
                </button>
              ))}
            </div>
          </div>

          {when && !Number.isNaN(when.getTime()) && (
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
              <p className="text-xs text-blue-300">
                Scheduled for:{' '}
                <strong className="text-blue-100">{formatPreview(when)}</strong>
              </p>
              <p className="text-[10px] text-blue-400/70 mt-1">
                24h clock: {localDateString(when)} {format24h(when)}
              </p>
            </div>
          )}

          {error && (
            <p className="text-xs text-red-400 bg-red-950/40 border border-red-900 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSchedule}
              disabled={loading || !scheduledDate || !scheduledTime}
              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {loading ? '⏳ Scheduling...' : '📅 Schedule'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
