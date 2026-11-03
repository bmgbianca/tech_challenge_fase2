import { useMemo, useState } from "react";
import Markdown from "./Markdown";
import { splitDriverInstructions } from "../instructions";

export default function DriverInstructionsModal({
  open,
  loading,
  instructions,
  vehiclesCount = 1,
  error,
  onClose,
  title = "Instruções para o motorista",
  loadingLabel = "Gerando instruções...",
  errorLabel = "Não foi possível gerar as instruções",
}) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  const driverTexts = useMemo(
    () => splitDriverInstructions(instructions, vehiclesCount),
    [instructions, vehiclesCount]
  );
  const hasTabs = driverTexts.length > 1;
  const activeText = driverTexts[Math.min(activeTab, driverTexts.length - 1)];

  if (!open) return null;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(activeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="instructions-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="instructions-modal-title"
    >
      <div className="instructions-modal__backdrop" onClick={onClose} />

      <div className="instructions-modal__card">
        <div className="instructions-modal__header">
          <h2 id="instructions-modal-title">{title}</h2>
          <button
            className="instructions-modal__close"
            onClick={onClose}
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <div className="instructions-modal__body">
          {loading && (
            <div className="instructions-modal__loading">
              <div className="loading-overlay__spinner" />
              <p>{loadingLabel}</p>
            </div>
          )}

          {!loading && error && (
            <div className="instructions-modal__error">
              {errorLabel}: {error}
            </div>
          )}

          {!loading && !error && instructions && hasTabs && (
            <div className="instructions-tabs" role="tablist">
              {driverTexts.map((_, index) => (
                <button
                  key={index}
                  role="tab"
                  id={`instructions-tab-${index}`}
                  aria-selected={index === activeTab}
                  aria-controls="instructions-tabpanel"
                  className={`instructions-tabs__tab${
                    index === activeTab ? " instructions-tabs__tab--active" : ""
                  }`}
                  onClick={() => {
                    setActiveTab(index);
                    setCopied(false);
                  }}
                >
                  Motorista {index + 1}
                </button>
              ))}
            </div>
          )}

          {!loading && !error && instructions && (
            <div
              role={hasTabs ? "tabpanel" : undefined}
              id={hasTabs ? "instructions-tabpanel" : undefined}
              aria-labelledby={hasTabs ? `instructions-tab-${activeTab}` : undefined}
            >
              <Markdown className="instructions-modal__text">{activeText}</Markdown>
            </div>
          )}
        </div>

        {!loading && !error && instructions && (
          <div className="instructions-modal__footer">
            <button className="secondary-button" onClick={handleCopy}>
              {copied ? "Copiado!" : hasTabs ? "Copiar texto deste motorista" : "Copiar texto"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
