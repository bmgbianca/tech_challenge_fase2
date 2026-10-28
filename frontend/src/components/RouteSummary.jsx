import { useEffect, useState } from "react";
import { fetchDriverInstructions } from "../api";
import DriverInstructionsModal from "./DriverInstructionsModal";

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
      const data = await fetchDriverInstructions(result.best_route);
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
          <div className="summary__label">Distância estimada</div>
          <div className="summary__value">
            {formatDistance(result?.best_distance)}
          </div>
        </div>
      </div>

      <div className="summary__item">
        <span>🕒</span>
        <div>
          <div className="summary__label">Tempo estimado</div>
          <div className="summary__value">
            {formatDuration(result?.total_duration)}
          </div>
        </div>
      </div>

      <div className="summary__item">
        <span>🏁</span>
        <div>
          <div className="summary__label">Número de paradas</div>
          <div className="summary__value">{result?.stops_count ?? "–"}</div>
        </div>
      </div>

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
        open={modalOpen}
        loading={loadingInstructions}
        instructions={instructions}
        error={instructionsError}
        onClose={() => setModalOpen(false)}
      />
    </aside>
  );
}
