'use client';

/** Topic + sports category chips for the news feed */
const GENERAL = [
  { id: 'all', label: '🌐 All' },
  { id: 'india', label: '🇮🇳 India' },
  { id: 'global', label: '🌍 Global' },
  { id: 'science', label: '🔬 Science' },
  { id: 'technology', label: '💻 Tech' },
  { id: 'space', label: '🚀 Space' },
  { id: 'ocean', label: '🌊 Ocean' },
  { id: 'facts', label: '💡 Facts' },
  { id: 'sports', label: '🏅 All Sports' },
];

const SPORTS = [
  { id: 'sports_local', label: '🇮🇳 Local sports' },
  { id: 'sports_international', label: '🌐 Int’l sports' },
  { id: 'sports_laliga', label: '🇪🇸 La Liga' },
  { id: 'sports_epl', label: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL' },
  { id: 'sports_tennis', label: '🎾 Tennis' },
  { id: 'sports_cricket', label: '🏏 Cricket' },
];

interface Props {
  selected: string;
  onChange: (category: string) => void;
}

function Chip({
  id,
  label,
  selected,
  onChange,
  activeClass = 'bg-blue-600 text-white',
}: {
  id: string;
  label: string;
  selected: string;
  onChange: (id: string) => void;
  activeClass?: string;
}) {
  const active = selected === id;
  return (
    <button
      type="button"
      onClick={() => onChange(id)}
      className={`text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
        active
          ? activeClass
          : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
      }`}
    >
      {label}
    </button>
  );
}

export default function SourceFilter({ selected, onChange }: Props) {
  const sportsActive =
    selected === 'sports' || selected.startsWith('sports_');

  return (
    <div className="flex flex-col items-end gap-1.5 max-w-full">
      <div className="flex gap-1 flex-wrap justify-end">
        {GENERAL.map((cat) => (
          <Chip
            key={cat.id}
            id={cat.id}
            label={cat.label}
            selected={selected}
            onChange={onChange}
            activeClass={
              cat.id === 'sports' || cat.id.startsWith('sports')
                ? 'bg-emerald-600 text-white'
                : 'bg-blue-600 text-white'
            }
          />
        ))}
      </div>
      {sportsActive && (
        <div className="flex gap-1 flex-wrap justify-end">
          {SPORTS.map((cat) => (
            <Chip
              key={cat.id}
              id={cat.id}
              label={cat.label}
              selected={selected}
              onChange={onChange}
              activeClass="bg-emerald-600 text-white"
            />
          ))}
        </div>
      )}
    </div>
  );
}

export { GENERAL as GENERAL_CATEGORIES, SPORTS as SPORTS_CATEGORIES };
