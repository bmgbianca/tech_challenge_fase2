import { useEffect, useState } from "react";
import { fetchRouteRuns, fetchComparativeReport } from "../api";
import ReportAccordion from "../components/ReportAccordion";

function formatDistance(km) {
  return `${km.toFixed(1)} km`;
}

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}min`;
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString("pt-BR");
}

function groupRunsByCitySet(runs) {
  const groups = new Map();

  for (const run of runs) {
    const key = JSON.stringify(run.city_set ?? [...run.best_route].sort());
    if (!groups.has(key)) {
      groups.set(key, {
        citySet: run.city_set ?? [...run.best_route].sort(),
        runs: [],
      });
    }
    groups.get(key).runs.push(run);
  }

  return [...groups.values()].map((group) => ({
    ...group,
    runs: group.runs.sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    ),
  }));
}

export default function ReportsPage() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);

  const [reportsByCitySet, setReportsByCitySet] = useState({});
  const [expandedByCitySet, setExpandedByCitySet] = useState({});
  const [loadingByCitySet, setLoadingByCitySet] = useState({});
  const [errorsByCitySet, setErrorsByCitySet] = useState({});

  useEffect(() => {
    fetchRouteRuns()
      .then(setRuns)
      .catch((err) => setError(err.message));
  }, []);

  const groups = runs ? groupRunsByCitySet(runs) : [];

  async function handleToggleReport(citySet) {
    const key = citySet.join("|");

    // Already open — just collapse it.
    if (expandedByCitySet[key]) {
      setExpandedByCitySet((current) => ({ ...current, [key]: false }));
      return;
    }

    setExpandedByCitySet((current) => ({ ...current, [key]: true }));

    // Already generated for this exact city set — reuse it, no new call.
    if (reportsByCitySet[key]) return;

    setLoadingByCitySet((current) => ({ ...current, [key]: true }));
    setErrorsByCitySet((current) => ({ ...current, [key]: null }));
    try {
      const data = await fetchComparativeReport(citySet);
      setReportsByCitySet((current) => ({ ...current, [key]: data.report }));
    } catch (err) {
      setErrorsByCitySet((current) => ({ ...current, [key]: err.message }));
    } finally {
      setLoadingByCitySet((current) => ({ ...current, [key]: false }));
    }
  }

  return (
    <main className="reports">
      <div className="reports__header">
        <h1>Relatórios</h1>
        <p>
          Comparativo das rotas otimizadas ao longo do tempo, agrupadas pelo
          conjunto de cidades utilizado em cada execução.
        </p>
      </div>

      {error && <div className="reports__error">{error}</div>}

      {!error && runs && runs.length === 0 && (
        <div className="reports__empty">
          Nenhuma rota foi gerada ainda. Vá até o Início e clique em "Gerar
          rota" para começar a acumular histórico.
        </div>
      )}

      {groups.map((group) => {
        const key = group.citySet.join("|");

        return (
          <section className="reports__group" key={key}>
            <div className="reports__group-header">
              <div>
                <h2>
                  Conjunto de {group.citySet.length} cidades
                  <span className="reports__group-count">
                    {group.runs.length} execuções
                  </span>
                </h2>
                <p className="reports__city-set">{group.citySet.join(", ")}</p>
              </div>

              <span className="tooltip">
                <button
                  className="icon-button"
                  aria-label="Gerar análise comparativa"
                  onClick={() => handleToggleReport(group.citySet)}
                >
                  📊
                </button>
                <span className="tooltip__text">Gerar análise comparativa</span>
              </span>
            </div>

            <div className="reports__table-wrapper">
              <table className="reports__table">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>População</th>
                    <th>Mutação</th>
                    <th>Gerações</th>
                    <th>Distância</th>
                    <th>Tempo estimado</th>
                  </tr>
                </thead>
                <tbody>
                  {group.runs.map((run) => (
                    <tr key={run.id}>
                      <td>{formatDate(run.created_at)}</td>
                      <td>
                        {run.population_type} ({run.population_size})
                      </td>
                      <td>{run.mutation_probability}</td>
                      <td>{run.generations_run}</td>
                      <td>{formatDistance(run.best_distance)}</td>
                      <td>{formatDuration(run.total_duration)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ReportAccordion
              open={!!expandedByCitySet[key]}
              loading={!!loadingByCitySet[key]}
              error={errorsByCitySet[key]}
              report={reportsByCitySet[key]}
              onCollapse={() =>
                setExpandedByCitySet((current) => ({ ...current, [key]: false }))
              }
              onExpand={() =>
                setExpandedByCitySet((current) => ({ ...current, [key]: true }))
              }
            />
          </section>
        );
      })}
    </main>
  );
}
