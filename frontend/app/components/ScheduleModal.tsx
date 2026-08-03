'use client';

import { useState } from 'react';

interface ScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSchedule: (scheduledAt: string) => void;
  loading: boolean;
}

export default function ScheduleModal({ isOpen, onClose, onSchedule, loading }: ScheduleModalProps) {
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('09:00');

  if (!isOpen) return null;

  const handleSchedule = () => {
    if (!scheduledDate) {
      alert('Please select a date');
      return;
    }
    const scheduledAt = new Date(`${scheduledDate}T${scheduledTime}`).toISOString();
    if (new Date(scheduledAt) <= new Date()) {
      alert('Scheduled time must be in the future');
      return;
    }
    onSchedule(scheduledAt);
  };

  // Get minimum date (today)
  const today = new Date().toISOString().split('T')[0];
  // Get maximum date (30 days from now)
  const maxDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split('T')[0];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-sm w-full">
        <h2 className="text-lg font-semibold text-white mb-4">📅 Schedule Tweet</h2>

        <div className="space-y-4">
          {/* Date Picker */}
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

          {/* Time Picker */}
          <div>
            <label className="text-sm text-gray-400 block mb-2">Time (24h format)</label>
            <input
              type="time"
              value={scheduledTime}
              onChange={(e) => setScheduledTime(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-2 text-white outline-none"
            />
          </div>

          {/* Recommended Times */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-2">💡 Recommended posting times:</p>
            <div className="grid grid-cols-3 gap-2">
              {['08:00', '12:00', '18:00'].map((time) => (
                <button
                  key={time}
                  onClick={() => setScheduledTime(time)}
                  className="text-xs px-2 py-1 bg-gray-700 hover:bg-blue-600 rounded transition-colors text-gray-300 hover:text-white"
                >
                  {time}
                </button>
              ))}
            </div>
          </div>

          {/* Preview */}
          {scheduledDate && (
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
              <p className="text-xs text-blue-300">
                Scheduled for:{' '}
                <strong>
                  {new Date(`${scheduledDate}T${scheduledTime}`).toLocaleString()}
                </strong>
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSchedule}
              disabled={loading || !scheduledDate}
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
