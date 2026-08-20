import type { BulkPromptState } from "../types";

export default function SimilarBulkDialog({
  prompt,
  onConfirm,
  onCancel,
}: {
  prompt: BulkPromptState;
  onConfirm: (issueIds: string[]) => void;
  onCancel: () => void;
}) {
  const total = prompt.similarIds.length;
  const actionLabel = prompt.action === "fix" ? "corregir" : "descartar";

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <h3>Errores idénticos en la diapositiva {prompt.anchor.slide}</h3>
        <p>
          Hay {total} errores con el mismo problema: <strong>{prompt.anchor.category}</strong>{" "}
          <em>«{prompt.anchor.actual}»</em>. ¿Quieres {actionLabel} todos?
        </p>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => onConfirm([prompt.anchor.issue_id!])}
          >
            Solo este
          </button>
          <button className="btn btn-primary" onClick={() => onConfirm(prompt.similarIds)}>
            Todos ({total})
          </button>
        </div>
      </div>
    </div>
  );
}
