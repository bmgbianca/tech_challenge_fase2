import { useEffect, useState } from "react";
import { fetchRouteRuns, fetchProcessRecommendations } from "../api";
import Markdown from "../components/Markdown";

export default function RecommendationsPage() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);

  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportError, setReportError] = useState(null);

  useEffect(() => {
    fetchRouteRuns()
      .then(setRuns)
      .catch((err) => setError(err.message));
  }, []);

  async function handleGenerate() {
    setLoading(true);
    setReportError(null);
    try {
      const data = await fetchProcessRecommendations();
      setRecommendations(data.report);
    } catch (err) {
      setReportError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="reports">
      <div className="reports__header">
        <h1>Recomendações</h1>
        <p>
          Padrões identificados em todo o histórico de execuções, com
          sugestões de melhoria de parâmetros e processo do algoritmo
          genético.
        </p>
      </div>

      {error && <div className="reports__error">{error}</div>}

      {!error && runs && runs.length === 0 && (
        <div className="reports__empty">
          Nenhuma rota foi gerada ainda. Vá até o Início e clique em "Gerar
          rota" para começar a acumular histórico.
        </div>
      )}

      {!error && runs && runs.length > 0 && (
        <section className="reports__group">
          <div className="reports__group-header">
            <div>
              <h2>Recomendações de processo</h2>
              <p className="reports__city-set">
                Baseado em {runs.length} execuções acumuladas até agora.
              </p>
            </div>

            {!recommendations && (
              <button
                className="secondary-button"
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading ? "Gerando..." : "Gerar recomendações"}
              </button>
            )}
          </div>

          {reportError && (
            <div className="report-accordion__error">
              Não foi possível gerar a análise: {reportError}
            </div>
          )}

          {recommendations && (
            <Markdown className="report-accordion__text">
              {recommendations}
            </Markdown>
          )}
        </section>
      )}
    </main>
  );
}
