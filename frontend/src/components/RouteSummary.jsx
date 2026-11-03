import { useEffect, useState } from "react";
import { fetchDriverInstructions } from "../api";
import DriverInstructionsModal from "./DriverInstructionsModal";
import { getVehicleColor, normalizeRoutes } from "../routes";

function formatDistance(km) {
  if (km == null) return "–";
  return `${km.toFixed(1)} km`;
}

function formatDuration(seconds) {
  if (seconds == null) return "–";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}min`;
}

function VehicleCard({ vehicle, index }) {
  const hasPriorities = vehicle.priority_cities_count > 0;

  return (
    <div
      className="vehicle-card"
      style={{ borderLeftColor: getVehicleColor(index) }}
    >
      <div className="vehicle-card__header">
        <strong>Veículo {vehicle.vehicle}</strong>
        {hasPriorities && (
          <span
            className={`vehicle-card__badge ${
              vehicle.priorities_on_time
                ? "vehicle-card__badge--ok"
                : "vehicle-card__badge--late"
            }`}
          >
            {vehicle.priorities_on_time
              ? "Prioridades no prazo"
              : "Prioridade atrasada"}
          </span>
        )}
      </div>

      <div className="vehicle-card__metrics">
        <span>📍 {formatDistance(vehicle.distance_km)}</span>
        <span>🕒 {formatDuration(vehicle.duration_seconds)}</span>
        <span>
          🏁 {vehicle.stops_count}{" "}
          {vehicle.stops_count === 1 ? "cidade" : "cidades"}
        </span>
      </div>

      <div className="vehicle-card__route">{vehicle.route.join(" → ")}</div>
    </div>
  );
}

export default function RouteSummary({ result, error }) {
  const [instructions, setInstructions] = useState(null);
  const [instructionsError, setInstructionsError] = useState(null);
  const [loadingInstructions, setLoadingInstructions] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    setInstructions(null);
    setInstructionsError(null);
    setModalOpen(false);
  }, [result]);

  async function handleGenerateInstructions() {
    if (!result?.best_route) return;

    // Already generated for the current route — just reopen the modal,
    // no need to call the LLM again (saves tokens).
    if (instructions) {
      setModalOpen(true);
      return;
    }

    setModalOpen(true);
    setLoadingInstructions(true);
    setInstructionsError(null);
    try {
      const data = await fetchDriverInstructions(
        result.best_route,
        result.cities
      );
      setInstructions(data.driver_instructions);
    } catch (err) {
      setInstructionsError(err.message);
    } finally {
      setLoadingInstructions(false);
    }
  }

  return (
    <aside className="summary">
      <div className="summary__header">
        <span>🔗</span>
        <h2>Resumo da rota</h2>
      </div>

      <div className="summary__item">
        <span>📍</span>
        <div>
          <div className="summary__label">Distância total (todos os veículos)</div>
          <div className="summary__value">
            {formatDistance(result?.best_distance)}
          </div>
        </div>
      </div>

      <div className="summary__item">
        <span>🕒</span>
        <div>
          <div className="summary__label">
            Tempo estimado
            {result?.vehicles_number > 1 ? " (veículo mais demorado)" : ""}
          </div>
          <div className="summary__value">
            {formatDuration(result?.total_duration)}
          </div>
        </div>
      </div>

      <div className="summary__item">
        <span>🚚</span>
        <div>
          <div className="summary__label">Veículos</div>
          <div className="summary__value">{result?.vehicles_number ?? "–"}</div>
        </div>
      </div>

      <div className="summary__item">
        <span>🏁</span>
        <div>
          <div className="summary__label">Cidades atendidas</div>
          <div className="summary__value">{result?.stops_count ?? "–"}</div>
        </div>
      </div>

      {result?.vehicles_summary?.length > 1 && (
        <div className="summary__vehicles">
          <h3>Por veículo</h3>
          {result.vehicles_summary.map((vehicle, index) => (
            <VehicleCard key={vehicle.vehicle} vehicle={vehicle} index={index} />
          ))}
        </div>
      )}

      <button
        className="secondary-button"
        onClick={handleGenerateInstructions}
        disabled={!result?.best_route || loadingInstructions}
      >
        {loadingInstructions ? "Gerando..." : "Gerar direcionamentos"}
      </button>

      {error && <div className="summary__error">{error}</div>}

      {!result && !error && (
        <div className="summary__hint">
          ℹ️ A rota será exibida no mapa após a geração.
        </div>
      )}

      <DriverInstructionsModal
        // New instructions remount the modal, so it starts on the first driver's tab:
        key={instructions ?? "no-instructions"}
        open={modalOpen}
        loading={loadingInstructions}
        instructions={instructions}
        vehiclesCount={normalizeRoutes(result?.best_route).length}
        error={instructionsError}
        onClose={() => setModalOpen(false)}
      />
    </aside>
  );
}
