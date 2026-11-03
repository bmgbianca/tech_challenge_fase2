import { useEffect, useState } from "react";
import { fetchRouteRuns, fetchComparativeReport } from "../api";
import ReportAccordion from "../components/ReportAccordion";
import { getCitySet } from "../routes";

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

const PERIODS = [
  { value: "all", label: "Todo o histórico", days: null },
  { value: "day", label: "Últimas 24 horas", days: 1 },
  { value: "week", label: "Últimos 7 dias", days: 7 },
];

function filterRunsByPeriod(runs, period) {
  const { days } = PERIODS.find((item) => item.value === period);
  if (days === null) return runs;

  const start = Date.now() - days * 24 * 60 * 60 * 1000;
  return runs.filter((run) => new Date(run.created_at).getTime() >= start);
}

// Runs are only comparable when they have the same cities AND the same
// number of vehicles, so both define a group.
function groupRunsByCitySet(runs) {
  const groups = new Map();

  for (const run of runs) {
    const citySet = getCitySet(run);
    const vehiclesNumber = run.vehicles_number ?? 1;
    const key = `${citySet.join("|")}#${vehiclesNumber}`;
    if (!groups.has(key)) {
      groups.set(key, { key, citySet, vehiclesNumber, runs: [] });
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
  const [period, setPeriod] = useState("all");

  const [reportsByCitySet, setReportsByCitySet] = useState({});
  const [expandedByCitySet, setExpandedByCitySet] = useState({});
  const [loadingByCitySet, setLoadingByCitySet] = useState({});
  const [errorsByCitySet, setErrorsByCitySet] = useState({});

  useEffect(() => {
    fetchRouteRuns()
      .then(setRuns)
      .catch((err) => setError(err.message));
  }, []);

  const periodRuns = runs ? filterRunsByPeriod(runs, period) : [];
  const groups = groupRunsByCitySet(periodRuns);

  // A report belongs to the period it was generated for, so changing the
  // period discards the reports already loaded on screen.
  function handlePeriodChange(event) {
    setPeriod(event.target.value);
    setReportsByCitySet({});
    setExpandedByCitySet({});
    setLoadingByCitySet({});
    setErrorsByCitySet({});
  }

  async function handleToggleReport(group) {
    const { key, citySet, vehiclesNumber } = group;

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
      const data = await fetchComparativeReport(
        citySet,
        vehiclesNumber,
        period
      );
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
          conjunto de cidades e número de veículos de cada execução. Escolha o
          período para gerar um relatório diário ou semanal.
        </p>
        <label className="reports__period">
          Período:{" "}
          <select value={period} onChange={handlePeriodChange}>
            {PERIODS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <div className="reports__error">{error}</div>}

      {!error && runs && runs.length === 0 && (
        <div className="reports__empty">
          Nenhuma rota foi gerada ainda. Vá até o Início e clique em "Gerar
          rota" para começar a acumular histórico.
        </div>
      )}

      {!error && runs && runs.length > 0 && groups.length === 0 && (
        <div className="reports__empty">
          Nenhuma execução no período selecionado.
        </div>
      )}

      {groups.map((group) => {
        const key = group.key;

        return (
          <section className="reports__group" key={key}>
            <div className="reports__group-header">
              <div>
                <h2>
                  Conjunto de {group.citySet.length} cidades ·{" "}
                  {group.vehiclesNumber}{" "}
                  {group.vehiclesNumber === 1 ? "veículo" : "veículos"}
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
                  onClick={() => handleToggleReport(group)}
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
                    <th>Veículos</th>
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
                      <td>{run.vehicles_number ?? 1}</td>
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
