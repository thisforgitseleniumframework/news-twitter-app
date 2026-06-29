'use client';

const CATEGORIES = [
  { id: 'all', label: '🌐 All' },
  { id: 'india', label: '🇮🇳 India' },
  { id: 'global', label: '🌍 Global' },
];

interface Props {
  selected: string;
  onChange: (category: string) => void;
}

export default function SourceFilter({ selected, onChange }: Props) {
  return (
    <div className="flex gap-1">
      {CATEGORIES.map((cat) => (
        <button
          key={cat.id}
          onClick={() => onChange(cat.id)}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
            selected === cat.id
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
          }`}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
}
