import { useEffect, useRef } from "react";

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}min`;
}

export default function RouteLog({ snapshots, currentIndex, error }) {
  const listRef = useRef(null);
  const entries = snapshots ? snapshots.slice(0, currentIndex + 1) : [];

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [entries.length]);

  return (
    <aside className="route-log">
      <div className="route-log__header">
        <h2>Log de gerações</h2>
      </div>

      {error && <div className="route-log__error">{error}</div>}

      <div className="route-log__list" ref={listRef}>
        {entries.length === 0 && !error && (
          <div className="route-log__hint">
            O log será preenchido conforme a rota é gerada.
          </div>
        )}

        {entries.map((snapshot) => (
          <div className="route-log__entry" key={snapshot.generation}>
            <span className="route-log__generation">
              Geração {snapshot.generation}
            </span>
            <span>Distância: {snapshot.best_distance.toFixed(1)} km</span>
            <span>Tempo estimado: {formatDuration(snapshot.best_duration)}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
