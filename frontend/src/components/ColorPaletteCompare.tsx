export default function ColorPaletteCompare({
  actual,
  suggestions,
  selected,
  onSelect,
  groupKey,
}: {
  actual: string;
  suggestions: Array<{ color: string; label: string }>;
  selected: string;
  onSelect: (color: string) => void;
  groupKey: string;
}) {
  const selectedSuggestion = suggestions.find((item) => item.color === selected) || suggestions[0];

  return (
    <div className="color-palette-compare">
      <div className="color-palette-cell">
        <div className="color-palette-swatch" style={{ backgroundColor: actual }} aria-hidden="true" />
        <span className="color-palette-label">Actual</span>
        <span className="color-palette-hex">{actual}</span>
      </div>
      <div className="color-palette-cell">
        <div
          className="color-palette-swatch"
          style={{ backgroundColor: selectedSuggestion?.color || selected }}
          aria-hidden="true"
        />
        <label className="color-palette-label" htmlFor={`palette-select-${groupKey}`}>
          Sugerido
        </label>
        <select
          id={`palette-select-${groupKey}`}
          className="color-palette-select"
          value={selected}
          onChange={(event) => onSelect(event.target.value)}
        >
          {suggestions.map((item) => (
            <option key={item.color} value={item.color}>
              {item.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
