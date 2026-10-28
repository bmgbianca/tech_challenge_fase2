export default function LoadingOverlay({
  visible,
  message = "Estamos trabalhando para encontrar a melhor rota.",
}) {
  if (!visible) return null;

  return (
    <div className="loading-overlay" role="alert" aria-live="assertive">
      <div className="loading-overlay__modal">
        <div className="loading-overlay__spinner" />
        <h2>Aguarde...</h2>
        <p>{message}</p>
      </div>
    </div>
  );
}
