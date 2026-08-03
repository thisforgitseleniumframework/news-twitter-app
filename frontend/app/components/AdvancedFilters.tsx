'use client';

import { useState } from 'react';

interface FilterProps {
  onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
  keyword: string;
  source: string;
  days: number | null;
  processed: boolean | null;
}

export default function AdvancedFilters({ onFilterChange }: FilterProps) {
  const [filters, setFilters] = useState<FilterState>({
    keyword: '',
    source: '',
    days: null,
    processed: null,
  });

  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = (key: keyof FilterState, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      keyword: '',
      source: '',
      days: null,
      processed: null,
    };
    setFilters(resetFilters);
    onFilterChange(resetFilters);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      {/* Basic Search */}
      <div>
        <input
          type="text"
          placeholder="🔍 Search articles by keyword..."
          value={filters.keyword}
          onChange={(e) => handleChange('keyword', e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg p-2 text-sm text-white outline-none transition-colors"
        />
      </div>

      {/* Toggle Advanced Filters */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 transition-colors"
      >
        {showAdvanced ? '▼ Advanced Filters' : '▶ Advanced Filters'}
      </button>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-800">
          {/* Source Filter */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Source</label>
            <input
              type="text"
              placeholder="Filter by source..."
              value={filters.source}
              onChange={(e) => handleChange('source', e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded p-1.5 text-xs text-white outline-none"
            />
          </div>

          {/* Days Filter */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Last N Days</label>
            <input
              type="number"
              placeholder="7"
              min="1"
              max="365"
              value={filters.days ?? ''}
              onChange={(e) => handleChange('days', e.target.value ? parseInt(e.target.value) : null)}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded p-1.5 text-xs text-white outline-none"
            />
          </div>

          {/* Processed Filter */}
          <div className="col-span-2">
            <label className="text-xs text-gray-400 block mb-1">Processing Status</label>
            <select
              value={filters.processed === null ? '' : filters.processed ? 'true' : 'false'}
              onChange={(e) =>
                handleChange('processed', e.target.value === '' ? null : e.target.value === 'true')
              }
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded p-1.5 text-xs text-white outline-none"
            >
              <option value="">All</option>
              <option value="false">Not Processed</option>
              <option value="true">Processed</option>
            </select>
          </div>

          {/* Reset Button */}
          <button
            onClick={handleReset}
            className="col-span-2 text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 transition-colors"
          >
            ↻ Reset Filters
          </button>
        </div>
      )}
    </div>
  );
}
