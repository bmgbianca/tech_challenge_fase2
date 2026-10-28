import { useState } from "react";
import Markdown from "./Markdown";

export default function DriverInstructionsModal({
  open,
  loading,
  instructions,
  error,
  onClose,
  title = "Instruções para o motorista",
  loadingLabel = "Gerando instruções...",
  errorLabel = "Não foi possível gerar as instruções",
}) {
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(instructions);
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

          {!loading && !error && instructions && (
            <Markdown className="instructions-modal__text">
              {instructions}
            </Markdown>
          )}
        </div>

        {!loading && !error && instructions && (
          <div className="instructions-modal__footer">
            <button className="secondary-button" onClick={handleCopy}>
              {copied ? "Copiado!" : "Copiar texto"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
