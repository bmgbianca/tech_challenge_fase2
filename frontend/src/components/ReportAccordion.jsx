import Markdown from "./Markdown";

export default function ReportAccordion({
  open,
  loading,
  error,
  report,
  onCollapse,
  onExpand,
}) {
  if (!open) {
    // Nothing has ever been generated for this group — no need to show
    // anything until the user clicks the 📊 button.
    if (!report && !error) return null;

    // Already generated once — keep a slim bar with a "+" to reopen it,
    // instead of disappearing completely.
    return (
      <div className="report-accordion report-accordion--collapsed">
        <button
          className="icon-button"
          aria-label="Expandir análise"
          onClick={onExpand}
        >
          +
        </button>
      </div>
    );
  }

  return (
    <div className="report-accordion">
      <div className="report-accordion__header">
        <button
          className="icon-button"
          aria-label="Recolher análise"
          onClick={onCollapse}
        >
          −
        </button>
      </div>

      {loading && (
        <div className="report-accordion__loading">
          <div className="loading-overlay__spinner" />
          <p>Gerando análise comparativa...</p>
        </div>
      )}

      {!loading && error && (
        <div className="report-accordion__error">
          Não foi possível gerar a análise: {error}
        </div>
      )}

      {!loading && !error && report && (
        <Markdown className="report-accordion__text">{report}</Markdown>
      )}
    </div>
  );
}
