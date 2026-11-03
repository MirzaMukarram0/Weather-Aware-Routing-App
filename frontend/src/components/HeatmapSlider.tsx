interface HeatmapSliderProps {
  hourIndex: number;
  maxHour: number;
  label: string;
  onChange: (hour: number) => void;
  disabled?: boolean;
}

export function HeatmapSlider({ hourIndex, maxHour, label, onChange, disabled }: HeatmapSliderProps) {
  return (
    <div className={`forecast-slider${disabled ? " forecast-slider--disabled" : ""}`}>
      <div className="forecast-slider__row">
        <span className="forecast-slider__time">{label}</span>
        <span className="forecast-slider__step">
          H+{hourIndex}
          <span className="forecast-slider__max"> / {maxHour}</span>
        </span>
      </div>
      <input
        id="hour-slider"
        className="forecast-slider__range"
        type="range"
        min={0}
        max={maxHour}
        value={hourIndex}
        disabled={disabled}
        aria-label="Corridor forecast hour"
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
