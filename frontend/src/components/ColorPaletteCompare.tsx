import type { PaletteColorOption } from "../constants/brandPalette";

export default function ColorPaletteCompare({
  actual,
  options,
  selected,
  onSelect,
  groupKey,
}: {
  actual: string;
  options: PaletteColorOption[];
  selected: string;
  onSelect: (color: string) => void;
  groupKey: string;
}) {
  const selectedOption = options.find((item) => item.color === selected) || options[0];

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
          style={{ backgroundColor: selectedOption?.color || selected }}
          aria-hidden="true"
        />
        <label className="color-palette-label" htmlFor={`palette-select-${groupKey}`}>
          Corrección
        </label>
        <select
          id={`palette-select-${groupKey}`}
          className="color-palette-select"
          value={selected}
          onChange={(event) => onSelect(event.target.value)}
        >
          {options.map((item) => (
            <option key={item.color} value={item.color}>
              {item.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
