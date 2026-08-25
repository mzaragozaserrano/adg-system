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
      <div className="color-palette-cell color-palette-cell-wide">
        <div
          className="color-palette-swatch"
          style={{ backgroundColor: selectedOption?.color || selected }}
          aria-hidden="true"
        />
        <span className="color-palette-label" id={`palette-label-${groupKey}`}>
          Paleta ADG
        </span>
        <span className="color-palette-hex">{selectedOption?.label || selected}</span>
        <div
          className="color-palette-options"
          role="radiogroup"
          aria-labelledby={`palette-label-${groupKey}`}
        >
          {options.map((item) => (
            <button
              key={item.color}
              type="button"
              className={`color-palette-option ${selected === item.color ? "selected" : ""}`}
              onClick={() => onSelect(item.color)}
              title={item.label}
              aria-label={item.label}
              aria-pressed={selected === item.color}
            >
              <span
                className="color-palette-option-swatch"
                style={{ backgroundColor: item.color }}
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
