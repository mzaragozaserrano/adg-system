import type { BulkPromptState } from "../types";
import { categoryLabel } from "../utils/issueLabels";

export default function SimilarBulkDialog({
  prompt,
  onConfirm,
  onCancel,
}: {
  prompt: BulkPromptState;
  onConfirm: (issueIds: string[]) => void;
  onCancel: () => void;
}) {
  const actionLabel = prompt.action === "fix" ? "corregir" : "descartar";
  const currentIds = prompt.currentIds?.length ? prompt.currentIds : [prompt.anchor.issue_id!];
  const isGroupMatch = Boolean(prompt.problemsLabel && (prompt.matchCount || 0) > 1);
  const total = isGroupMatch ? (prompt.matchCount || 0) : prompt.similarIds.length;
  const allLabel = isGroupMatch ? `Todos (${total} textos)` : `Todos (${total})`;

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <h3>Errores idénticos en la diapositiva {prompt.anchor.slide}</h3>
        {isGroupMatch ? (
          <p>
            Hay {total} textos con los mismos errores: <strong>{prompt.problemsLabel}</strong>.
            ¿Quieres {actionLabel} todos?
          </p>
        ) : (
          <p>
            Hay {prompt.similarIds.length} errores con el mismo problema:{" "}
            <strong>{categoryLabel(prompt.anchor.category)}</strong> <em>«{prompt.anchor.actual}»</em>.
            ¿Quieres {actionLabel} todos?
          </p>
        )}
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => onConfirm(currentIds)}
          >
            Solo este
          </button>
          <button className="btn btn-primary" onClick={() => onConfirm(prompt.similarIds)}>
            {allLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
