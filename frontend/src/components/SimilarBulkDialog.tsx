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
        <h3>Errores similares en la diapositiva {prompt.anchor.slide}</h3>
        <p>
          ¿Quieres {actionLabel} todos los errores de <strong>{prompt.anchor.category}</strong> en esta diapositiva?
          Hay {total} en total.
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
