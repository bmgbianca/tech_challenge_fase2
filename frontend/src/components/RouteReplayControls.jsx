const SPEED_OPTIONS = [0.5, 1, 2, 5];

export default function RouteReplayControls({
  snapshots,
  currentIndex,
  isPlaying,
  onChangeIndex,
  onTogglePlay,
  playbackSpeed,
  onChangeSpeed,
}) {
  if (!snapshots || snapshots.length === 0) return null;

  const current = snapshots[currentIndex];
  const isLast = currentIndex === snapshots.length - 1;

  return (
    <div className="replay-controls">
      <button
        className="replay-controls__play"
        onClick={onTogglePlay}
        aria-label={isPlaying ? "Pausar replay" : "Reproduzir replay"}
      >
        {isPlaying ? "⏸" : isLast ? "🔁" : "▶"}
      </button>

      <input
        type="range"
        min={0}
        max={snapshots.length - 1}
        step={1}
        value={currentIndex}
        onChange={(event) => onChangeIndex(Number(event.target.value))}
        className="replay-controls__slider"
      />

      <select
        className="replay-controls__speed"
        value={playbackSpeed}
        onChange={(event) => onChangeSpeed(Number(event.target.value))}
        aria-label="Velocidade do replay"
      >
        {SPEED_OPTIONS.map((speed) => (
          <option key={speed} value={speed}>
            {speed}x
          </option>
        ))}
      </select>

      <div className="replay-controls__label">
        <span>Geração {current.generation}</span>
        <span>{current.best_distance.toFixed(1)} km</span>
      </div>
    </div>
  );
}
