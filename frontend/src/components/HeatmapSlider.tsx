interface HeatmapSliderProps {
  hourIndex: number;
  maxHour: number;
  label: string;
  onChange: (hour: number) => void;
  disabled?: boolean;
}

export function HeatmapSlider({ hourIndex, maxHour, label, onChange, disabled }: HeatmapSliderProps) {
  return (
    <div className="heatmap-slider">
      <label htmlFor="hour-slider">Corridor forecast: {label}</label>
      <input
        id="hour-slider"
        type="range"
        min={0}
        max={maxHour}
        value={hourIndex}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span>
        Hour {hourIndex} / {maxHour}
      </span>
    </div>
  );
}
