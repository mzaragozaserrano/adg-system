import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Navigate, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import {
  downloadReportPdf,
  fetchHistory,
  fetchThumbnail,
  fetchValidation,
  fixPresentation,
  googleLoginUrl,
  validateSlides,
} from "./api";
import { describeMimeType, isGoogleSlidesMime, openSlidesPicker } from "./googlePicker";
import { resolvePickerConfig } from "./pickerConfig";
import { useAuth } from "./auth";

interface Issue {
  issue_id?: string;
  slide: number;
  category: string;
  message: string;
  expected: string;
  actual: string;
  severity: string;
  severity_label: string;
  text_preview?: string;
  is_fixable?: boolean;
  fix_type?: string;
  object_id?: string;
  fix_payload?: Record<string, unknown>;
  text_range?: { start: number; end: number };
  color_actual?: string;
  color_suggested?: string;
  color_suggestions?: Array<{ color: string; label: string }>;
}

function hasFixMetadata(issue: Issue): boolean {
  return Boolean(issue.fix_type && issue.object_id && issue.fix_payload);
}

interface ValidationResult {
  source: string;
  source_type: string;
  total_slides: number;
  passed: boolean;
  grave_count: number;
  posible_count: number;
  fixable_count?: number;
  presentation_id?: string;
  validation_id?: string;
  working_presentation_id?: string;
  working_presentation_url?: string;
  issues: Issue[];
}

function enrichValidationResult(data: ValidationResult): ValidationResult {
  const pid = data.presentation_id || "doc";
  const issues = data.issues.map((issue, index) => {
    const enriched: Issue = {
      ...issue,
      issue_id: issue.issue_id || `${pid}-${issue.slide}-idx${index}-${issue.category}`,
    };
    return {
      ...enriched,
      is_fixable: hasFixMetadata(enriched),
    };
  });
  const fixable_count = issues.filter((i) => i.is_fixable).length;
  const grave_count = issues.filter((i) => i.severity === "grave").length;
  const posible_count = issues.filter((i) => i.severity === "posible").length;
  return {
    ...data,
    issues,
    fixable_count,
    grave_count,
    posible_count,
    passed: grave_count === 0,
  };
}

function removeIssuesFromResult(result: ValidationResult, issueIds: string[]): ValidationResult {
  const fixed = new Set(issueIds);
  const issues = result.issues.filter((issue) => !issue.issue_id || !fixed.has(issue.issue_id));
  const grave_count = issues.filter((i) => i.severity === "grave").length;
  const posible_count = issues.filter((i) => i.severity === "posible").length;
  const fixable_count = issues.filter((i) => i.is_fixable).length;
  return {
    ...result,
    issues,
    grave_count,
    posible_count,
    fixable_count,
    passed: grave_count === 0,
  };
}

function buildFixPayload(issue: Issue, colorOverride?: string) {
  const fixPayload = issue.fix_payload ? { ...issue.fix_payload } : {};
  if (
    colorOverride
    && issue.fix_type
    && ["text_color", "fill_color", "background_color"].includes(issue.fix_type)
  ) {
    fixPayload.color = colorOverride;
  }
  return {
    issue_id: issue.issue_id!,
    object_id: issue.object_id!,
    fix_type: issue.fix_type!,
    fix_payload: fixPayload,
    text_range: issue.text_range,
  };
}

function paletteGroupKey(issue: Issue): string | null {
  if (!issue.color_actual) return null;
  return `${issue.slide}:${issue.color_actual.toUpperCase()}`;
}

function similarIssueIds(issues: Issue[], anchor: Issue, fixableOnly = false): string[] {
  return issues
    .filter(
      (issue) =>
        issue.issue_id
        && issue.slide === anchor.slide
        && issue.category === anchor.category
        && (!fixableOnly || hasFixMetadata(issue))
    )
    .map((issue) => issue.issue_id!);
}

function buildColorOverridesForIssues(
  issues: Issue[],
  issueIds: string[],
  paletteSelections: Record<string, string>
): Record<string, string> | undefined {
  const overrides: Record<string, string> = {};
  for (const issueId of issueIds) {
    const issue = issues.find((item) => item.issue_id === issueId);
    if (!issue?.color_actual) continue;
    const key = paletteGroupKey(issue);
    const color = key
      ? paletteSelections[key] || issue.color_suggestions?.[0]?.color || issue.color_suggested
      : issue.color_suggested;
    if (color) overrides[issueId] = color;
  }
  return Object.keys(overrides).length > 0 ? overrides : undefined;
}

function slidesEditUrl(presentationId: string): string {
  return `https://docs.google.com/presentation/d/${presentationId}/edit`;
}

function ColorPaletteCompare({
  actual,
  suggestions,
  selected,
  onSelect,
  groupKey,
}: {
  actual: string;
  suggestions: Array<{ color: string; label: string }>;
  selected: string;
  onSelect: (color: string) => void;
  groupKey: string;
}) {
  const selectedSuggestion = suggestions.find((item) => item.color === selected) || suggestions[0];

  return (
    <div className="color-palette-compare">
      <div className="color-palette-cell">
        <div className="color-palette-swatch" style={{ backgroundColor: actual }} aria-hidden="true" />
        <span className="color-palette-label">Actual</span>
        <span className="color-palette-hex">{actual}</span>
      </div>
      <div className="color-palette-cell">
        <div
          className="color-palette-swatch"
          style={{ backgroundColor: selectedSuggestion?.color || selected }}
          aria-hidden="true"
        />
        <label className="color-palette-label" htmlFor={`palette-select-${groupKey}`}>
          Sugerido
        </label>
        <select
          id={`palette-select-${groupKey}`}
          className="color-palette-select"
          value={selected}
          onChange={(event) => onSelect(event.target.value)}
        >
          {suggestions.map((item) => (
            <option key={item.color} value={item.color}>
              {item.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

type BulkAction = "fix" | "discard";

interface BulkPromptState {
  action: BulkAction;
  anchor: Issue;
  similarIds: string[];
}

function SimilarBulkDialog({
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

type FixState = "idle" | "fixing" | "fixed" | "error";

interface FixJob {
  issueIds: string[];
  scopeKey: string;
  colorOverride?: string;
  colorByIssueId?: Record<string, string>;
}

function fixButtonLabel(state: FixState, defaultLabel: string): string {
  if (state === "fixing") return "Fixing";
  if (state === "fixed") return "Fixed";
  if (state === "error") return "Error";
  return defaultLabel;
}

function useFixQueue(
  onExecute: (
    issueIds: string[],
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => Promise<void>,
  onError?: (message: string) => void
) {
  const [fixStates, setFixStates] = useState<Record<string, FixState>>({});
  const queueRef = useRef<FixJob[]>([]);
  const processingRef = useRef(false);
  const fixStatesRef = useRef(fixStates);
  const onExecuteRef = useRef(onExecute);
  const onErrorRef = useRef(onError);

  fixStatesRef.current = fixStates;
  onExecuteRef.current = onExecute;
  onErrorRef.current = onError;

  const drainQueue = useCallback(async () => {
    if (processingRef.current) return;

    const job = queueRef.current.shift();
    if (!job) return;

    processingRef.current = true;
    try {
      await onExecuteRef.current(job.issueIds, {
        colorOverride: job.colorOverride,
        colorByIssueId: job.colorByIssueId,
      });
      setFixStates((prev) => {
        const next = { ...prev };
        for (const id of job.issueIds) delete next[id];
        if (job.scopeKey === "batch") delete next.batch;
        return next;
      });
    } catch (err) {
      onErrorRef.current?.(err instanceof Error ? err.message : "Error al corregir");
      setFixStates((prev) => {
        const next = { ...prev };
        for (const id of job.issueIds) {
          if (next[id] === "fixing") next[id] = "error";
        }
        if (job.scopeKey === "batch" && next.batch === "fixing") next.batch = "error";
        return next;
      });
    } finally {
      processingRef.current = false;
      void drainQueue();
    }
  }, []);

  const enqueue = useCallback((
    issueIds: string[],
    scopeKey: string,
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => {
    if (issueIds.length === 0) return;

    const states = fixStatesRef.current;
    if (issueIds.some((id) => states[id] === "fixing")) return;
    if (scopeKey === "batch" && states.batch === "fixing") return;

    setFixStates((prev) => {
      const next = { ...prev };
      for (const id of issueIds) next[id] = "fixing";
      if (scopeKey === "batch") next.batch = "fixing";
      return next;
    });

    queueRef.current.push({
      issueIds,
      scopeKey,
      colorOverride: options?.colorOverride,
      colorByIssueId: options?.colorByIssueId,
    });
    void drainQueue();
  }, [drainQueue]);

  const reset = useCallback(() => {
    queueRef.current = [];
    processingRef.current = false;
    setFixStates({});
  }, []);

  const clearBatchScope = useCallback(() => {
    setFixStates((prev) => {
      if (prev.batch !== "fixed" && prev.batch !== "error") return prev;
      const next = { ...prev };
      delete next.batch;
      return next;
    });
  }, []);

  return { enqueue, reset, clearBatchScope, fixStates };
}

const thumbnailCache = new Map<string, string>();

function thumbnailCacheKey(presentationId: string, slideNumber: number): string {
  return `${presentationId}:${slideNumber}`;
}

export function clearThumbnailCache(): void {
  for (const url of thumbnailCache.values()) {
    URL.revokeObjectURL(url);
  }
  thumbnailCache.clear();
}

function preloadSlideThumbnails(
  presentationId: string,
  slideNumbers: number[],
  onLoaded?: () => void
) {
  const pending = slideNumbers.filter((slideNumber) => !thumbnailCache.has(thumbnailCacheKey(presentationId, slideNumber)));
  if (pending.length === 0) {
    onLoaded?.();
    return;
  }

  let remaining = pending.length;
  const concurrency = 6;
  let cursor = 0;

  const worker = async () => {
    while (cursor < pending.length) {
      const slideNumber = pending[cursor];
      cursor += 1;
      const key = thumbnailCacheKey(presentationId, slideNumber);
      try {
        const url = await fetchThumbnail(presentationId, slideNumber);
        thumbnailCache.set(key, url);
      } catch {
        // ignore failed thumbnails
      } finally {
        remaining -= 1;
        onLoaded?.();
        if (remaining <= 0) return;
      }
    }
  };

  void Promise.all(Array.from({ length: Math.min(concurrency, pending.length) }, () => worker()));
}

function SlideThumbnail({
  presentationId,
  slideNumber,
  variant = "summary",
  showLabel = variant === "issue",
  cacheVersion = 0,
}: {
  presentationId: string;
  slideNumber: number;
  variant?: "summary" | "issue";
  showLabel?: boolean;
  cacheVersion?: number;
}) {
  const cacheKey = thumbnailCacheKey(presentationId, slideNumber);
  const [src, setSrc] = useState<string | null>(() => thumbnailCache.get(cacheKey) || null);
  const [loading, setLoading] = useState(!thumbnailCache.has(cacheKey));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const cached = thumbnailCache.get(cacheKey);
    if (cached) {
      setSrc(cached);
      setLoading(false);
      setFailed(false);
      return;
    }

    let active = true;
    setLoading(true);
    setFailed(false);
    fetchThumbnail(presentationId, slideNumber)
      .then((url) => {
        thumbnailCache.set(cacheKey, url);
        if (active) {
          setSrc(url);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [cacheKey, presentationId, slideNumber, cacheVersion]);

  const className = variant === "issue" ? "slide-thumb slide-thumb-issue" : "slide-thumb slide-thumb-summary";

  if (loading) {
    return (
      <div className={`${className} slide-thumb-placeholder`} aria-label={`Cargando diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
      </div>
    );
  }

  if (failed || !src) {
    return (
      <div className={`${className} slide-thumb-placeholder slide-thumb-missing`} aria-label={`Diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
      </div>
    );
  }

  return (
    <div className="slide-thumb-wrap">
      <img className={className} src={src} alt={`Diapositiva ${slideNumber}`} />
      {showLabel && <span className="slide-thumb-label">Diap. {slideNumber}</span>}
    </div>
  );
}

function slideSummary(issues: Issue[]) {
  const graves = issues.filter((i) => i.severity === "grave").length;
  const posibles = issues.filter((i) => i.severity === "posible").length;
  const parts = [`${issues.length} error(es)`];
  if (graves) parts.push(`${graves} grave(s)`);
  if (posibles) parts.push(`${posibles} posible(s)`);
  return parts.join(" · ");
}

function LoginPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Cargando...</div>;
  if (user) return <Navigate to="/" replace />;

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="badge">Validador · v2.0</div>
        <h1>Validador de Identidad ADG</h1>
        <p>Accede con tu cuenta corporativa de Google para validar y corregir presentaciones.</p>
        <a className="btn btn-primary" href={googleLoginUrl()}>
          Iniciar sesión con Google
        </a>
      </div>
    </div>
  );
}

function AuthCallback() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("No se recibió token de autenticación");
      return;
    }
    login(token)
      .then(() => navigate("/", { replace: true }))
      .catch(() => setError("Error al iniciar sesión"));
  }, [params, login, navigate]);

  if (error) return <div className="error-banner">{error}</div>;
  return <div className="loading">Completando inicio de sesión...</div>;
}

function ResultsView({
  result,
  onEnqueueFix,
  onDiscard,
  onThumbnailCached,
  onClearBatchScope,
  fixStates,
  canFix,
  originalPresentationId,
  workingPresentationId,
  appliedFixCount,
  fixedPresentationUrl,
  thumbCacheVersion,
}: {
  result: ValidationResult;
  onEnqueueFix: (
    issueIds: string[],
    scopeKey: string,
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => void;
  onDiscard: (issueIds: string[]) => void;
  onThumbnailCached: () => void;
  onClearBatchScope: () => void;
  fixStates: Record<string, FixState>;
  canFix: boolean;
  originalPresentationId: string | null;
  workingPresentationId: string | null;
  appliedFixCount: number;
  fixedPresentationUrl: string | null;
  thumbCacheVersion: number;
}) {
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string[]>([]);
  const [selectedIssues, setSelectedIssues] = useState<Set<string>>(new Set());
  const [paletteSelections, setPaletteSelections] = useState<Record<string, string>>({});
  const [bulkPrompt, setBulkPrompt] = useState<BulkPromptState | null>(null);

  useEffect(() => {
    const defaults: Record<string, string> = {};
    for (const issue of result.issues) {
      const key = paletteGroupKey(issue);
      if (!key || defaults[key]) continue;
      const first = issue.color_suggestions?.[0]?.color || issue.color_suggested;
      if (first) defaults[key] = first;
    }
    setPaletteSelections(defaults);
  }, [result.validation_id]);

  const categories = useMemo(
    () => Array.from(new Set(result.issues.map((i) => i.category))),
    [result.issues]
  );

  useEffect(() => {
    setSeverityFilter([]);
    setCategoryFilter([]);
    setSelectedIssues(new Set());
  }, [result.validation_id]);

  const filtered = result.issues.filter((issue) => {
    const severityOk = severityFilter.length === 0 || severityFilter.includes(issue.severity);
    const categoryOk = categoryFilter.length === 0 || categoryFilter.includes(issue.category);
    return severityOk && categoryOk;
  });

  const grouped = filtered.reduce<Record<number, Issue[]>>((acc, issue) => {
    acc[issue.slide] = acc[issue.slide] || [];
    acc[issue.slide].push(issue);
    return acc;
  }, {});

  const slideNumbers = Object.keys(grouped)
    .map(Number)
    .sort((a, b) => a - b);

  const selectedFixable = Array.from(selectedIssues).filter((id) =>
    result.issues.some((i) => i.issue_id === id)
  );
  const selectedFixableKey = selectedFixable.slice().sort().join(",");
  const batchState: FixState = fixStates.batch || "idle";

  useEffect(() => {
    if (batchState === "fixing") return;
    onClearBatchScope();
  }, [selectedFixableKey, batchState, onClearBatchScope]);

  function toggleIssue(id: string) {
    setSelectedIssues((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleFilter(
    value: string,
    setter: Dispatch<SetStateAction<string[]>>
  ) {
    setter((prev) =>
      prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value]
    );
  }

  function discardIssues(issueIds: string[]) {
    onDiscard(issueIds);
    setSelectedIssues((prev) => {
      const next = new Set(prev);
      issueIds.forEach((id) => next.delete(id));
      return next;
    });
  }

  function getPaletteSelection(issue: Issue): string {
    const key = paletteGroupKey(issue);
    if (!key) return issue.color_suggested || "";
    return paletteSelections[key] || issue.color_suggestions?.[0]?.color || issue.color_suggested || "";
  }

  function setPaletteSelection(issue: Issue, color: string) {
    const key = paletteGroupKey(issue);
    if (!key) return;
    setPaletteSelections((prev) => ({ ...prev, [key]: color }));
  }

  function applyFix(issueIds: string[]) {
    if (issueIds.length === 0) return;
    const colorByIssueId = buildColorOverridesForIssues(result.issues, issueIds, paletteSelections);
    const scopeKey = issueIds.length === 1 ? issueIds[0] : `bulk-${issueIds[0]}`;
    onEnqueueFix(issueIds, scopeKey, { colorByIssueId });
  }

  function requestFix(issue: Issue) {
    if (!issue.issue_id) return;
    const similarIds = similarIssueIds(result.issues, issue, true);
    if (similarIds.length <= 1) {
      applyFix([issue.issue_id]);
      return;
    }
    setBulkPrompt({ action: "fix", anchor: issue, similarIds });
  }

  function requestDiscard(issue: Issue) {
    if (!issue.issue_id) return;
    const similarIds = similarIssueIds(result.issues, issue, false);
    if (similarIds.length <= 1) {
      discardIssues([issue.issue_id]);
      return;
    }
    setBulkPrompt({ action: "discard", anchor: issue, similarIds });
  }

  function confirmBulkPrompt(issueIds: string[]) {
    if (!bulkPrompt) return;
    if (bulkPrompt.action === "fix") {
      applyFix(issueIds);
    } else {
      discardIssues(issueIds);
    }
    setBulkPrompt(null);
  }

  const statusClass = result.passed ? "status-ok" : result.grave_count > 0 ? "status-error" : "status-warn";
  const thumbPresentationId = originalPresentationId || result.presentation_id;
  const sourcePresentationId = originalPresentationId || result.presentation_id;
  const fixableInView = result.issues.filter((i) => i.is_fixable).length;

  useEffect(() => {
    if (!thumbPresentationId) return;
    const slideNumbers = Array.from(new Set(result.issues.map((issue) => issue.slide)));
    preloadSlideThumbnails(thumbPresentationId, slideNumbers, onThumbnailCached);
  }, [thumbPresentationId, result.validation_id, result.issues.length, onThumbnailCached]);

  return (
    <div className="results">
      {bulkPrompt && (
        <SimilarBulkDialog
          prompt={bulkPrompt}
          onConfirm={confirmBulkPrompt}
          onCancel={() => setBulkPrompt(null)}
        />
      )}
      <div className={`status-banner ${statusClass}`}>
        {result.passed
          ? "Presentación conforme con el manual ADG"
          : `${result.grave_count} error(es) grave(s), ${result.posible_count} posible(s)`}
      </div>

      {canFix && sourcePresentationId && (
        <div className="slides-action-bar">
          <div>
            <strong>Presentación en Google Slides</strong>
            <p>
              {fixableInView > 0
                ? `Hay ${fixableInView} error(es) corregible(s). Expande cada diapositiva para usar «Corregir» o selección múltiple.`
                : "No hay errores corregibles automáticamente en esta validación."}
            </p>
          </div>
          <div className="slides-action-bar-buttons">
            <a
              href={slidesEditUrl(sourcePresentationId)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
            >
              Abrir en Google Slides
            </a>
          </div>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-box"><div className="number">{result.total_slides}</div><div className="label">Diapositivas</div></div>
        <div className="stat-box"><div className="number">{result.grave_count}</div><div className="label">Graves</div></div>
        <div className="stat-box"><div className="number">{result.posible_count}</div><div className="label">Posibles</div></div>
        <div className="stat-box"><div className="number">{result.fixable_count || 0}</div><div className="label">Corregibles</div></div>
      </div>

      <div className="filters">
        <p className="filter-hint">Sin filtros activos se muestran todos. Marca uno o más para acotar la lista.</p>
        <div className="filter-group">
          <span className="filter-label">Severidad</span>
          {["grave", "posible"].map((s) => (
            <button
              key={s}
              className={`pill ${severityFilter.includes(s) ? "active" : ""}`}
              onClick={() => toggleFilter(s, setSeverityFilter)}
            >
              {s === "grave" ? "ERROR GRAVE" : "POSIBLE ERROR"}
            </button>
          ))}
        </div>
        <div className="filter-group">
          <span className="filter-label">Categoría</span>
          {categories.map((c) => (
            <button
              key={c}
              className={`pill ${categoryFilter.includes(c) ? "active" : ""}`}
              onClick={() => toggleFilter(c, setCategoryFilter)}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {canFix && selectedFixable.length > 0 && (
        <div className="fix-actions">
          <button
            className={`btn btn-primary btn-fix-batch btn-fix-${batchState}`}
            disabled={batchState === "fixing"}
            onClick={() => onEnqueueFix(selectedFixable, "batch")}
          >
            {fixButtonLabel(batchState, `Corregir seleccionados (${selectedFixable.length})`)}
          </button>
        </div>
      )}

      {workingPresentationId && appliedFixCount > 0 && fixedPresentationUrl && (
        <div className="export-bar">
          <div>
            <strong>Presentación corregida en Google Slides</strong>
            <p>
              {appliedFixCount} corrección(es) aplicada(s) sobre una única copia en Drive. El archivo original no se ha modificado.
            </p>
          </div>
          <div className="export-bar-actions">
            <a
              href={fixedPresentationUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
            >
              Abrir presentación corregida
            </a>
          </div>
        </div>
      )}

      {slideNumbers.map((slide) => {
        const issues = grouped[slide];
        return (
          <details key={slide} className="slide-group">
            <summary>
              <span className="slide-summary-text">
                <strong>Diapositiva {slide}</strong>
                <span className="slide-summary-count">{slideSummary(issues)}</span>
              </span>
              {thumbPresentationId && (
                <SlideThumbnail
                  presentationId={thumbPresentationId}
                  slideNumber={slide}
                  showLabel
                  cacheVersion={thumbCacheVersion}
                />
              )}
            </summary>
            {issues.map((issue) => {
              const issueState: FixState = issue.issue_id ? (fixStates[issue.issue_id] || "idle") : "idle";
              const issueBusy = issueState === "fixing";
              const paletteSuggestions =
                issue.color_suggestions
                || (issue.color_suggested
                  ? [{ color: issue.color_suggested, label: issue.expected }]
                  : []);
              const groupKey = paletteGroupKey(issue);
              const isPaletteIssue = Boolean(issue.color_actual && paletteSuggestions.length > 0);
              return (
              <div key={issue.issue_id || `${issue.slide}-${issue.message}`} className={`issue-card issue-${issue.severity}`}>
                <div className="issue-top-row">
                  {canFix && issue.issue_id && (
                    <label className="fix-checkbox">
                      <input
                        type="checkbox"
                        checked={selectedIssues.has(issue.issue_id)}
                        disabled={issueBusy}
                        onChange={() => toggleIssue(issue.issue_id!)}
                      />
                      Seleccionar
                    </label>
                  )}
                  <div className="issue-actions">
                    {canFix && issue.issue_id && issue.is_fixable && (
                      <button
                        className={`btn btn-fix btn-fix-${issueState}`}
                        disabled={issueBusy}
                        onClick={() => requestFix(issue)}
                      >
                        {fixButtonLabel(issueState, "Corregir")}
                      </button>
                    )}
                    {issue.issue_id && (
                      <button
                        className="btn btn-discard"
                        disabled={issueBusy}
                        onClick={() => requestDiscard(issue)}
                      >
                        Descartar
                      </button>
                    )}
                  </div>
                </div>
                <div className="issue-header">
                  <span className="severity-tag">{issue.severity_label}</span>
                  <span className="category-tag">{issue.category}</span>
                </div>
                <p className="issue-message">{issue.message}</p>
                {issue.text_preview && <p className="issue-preview">«{issue.text_preview}»</p>}
                {isPaletteIssue && groupKey ? (
                  <ColorPaletteCompare
                    actual={issue.color_actual!}
                    suggestions={paletteSuggestions}
                    selected={getPaletteSelection(issue)}
                    onSelect={(color) => setPaletteSelection(issue, color)}
                    groupKey={groupKey}
                  />
                ) : (
                  <div className="issue-meta">
                    <div><strong>Esperado:</strong> {issue.expected}</div>
                    <div><strong>Actual:</strong> {issue.actual}</div>
                  </div>
                )}
              </div>
            );
            })}
          </details>
        );
      })}

      <div className="report-section">
        <h3>Informe de validación</h3>
        <p className="report-hint">
          Estos archivos documentan los errores detectados. La presentación corregida se genera en Google Slides con los botones «Corregir».
        </p>
        <div className="download-section">
          {result.validation_id && (
            <button className="btn btn-secondary" onClick={() => downloadReportPdf(result.validation_id!)}>
              Informe PDF
            </button>
          )}
          <button
            className="btn btn-ghost"
            onClick={() => {
              const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "informe_validacion.json";
              a.click();
            }}
          >
            Exportar JSON
          </button>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const { user, logout } = useAuth();
  const [slidesUrl, setSlidesUrl] = useState("");
  const [selectedSlidesName, setSelectedSlidesName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [originalPresentationId, setOriginalPresentationId] = useState<string | null>(null);
  const [workingPresentationId, setWorkingPresentationId] = useState<string | null>(null);
  const [fixedPresentationUrl, setFixedPresentationUrl] = useState<string | null>(null);
  const [appliedFixCount, setAppliedFixCount] = useState(0);
  const [thumbCacheVersion, setThumbCacheVersion] = useState(0);
  const [history, setHistory] = useState<Array<{ id: number; source: string; passed: boolean; created_at: string }>>([]);

  const originalPresentationIdRef = useRef(originalPresentationId);
  const workingPresentationIdRef = useRef(workingPresentationId);
  const resultRef = useRef(result);

  originalPresentationIdRef.current = originalPresentationId;
  workingPresentationIdRef.current = workingPresentationId;
  resultRef.current = result;

  const executeFix = useCallback(async (
    issueIds: string[],
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => {
    const current = resultRef.current;
    const originalId = originalPresentationIdRef.current || current?.presentation_id;
    const workingId = workingPresentationIdRef.current;
    if (!originalId || !workingId || issueIds.length === 0 || !current) {
      throw new Error("No se puede corregir esta presentación");
    }

    const issuesToFix = current.issues.filter(
      (issue) => issue.issue_id && issueIds.includes(issue.issue_id) && hasFixMetadata(issue)
    );
    if (issuesToFix.length === 0) {
      throw new Error("No hay correcciones aplicables para los errores seleccionados");
    }

    const data = await fixPresentation(
      workingId,
      issuesToFix.map((issue) => buildFixPayload(
        issue,
        options?.colorByIssueId?.[issue.issue_id!] ?? options?.colorOverride
      )),
      originalId,
      "in_place"
    );
    setFixedPresentationUrl(data.fixed_url);
    setAppliedFixCount((prev) => prev + (data.fixes_applied || 0));
    setResult((prev) => (prev ? removeIssuesFromResult(prev, issueIds) : prev));
  }, []);

  function handleDiscard(issueIds: string[]) {
    setResult((prev) => (prev ? removeIssuesFromResult(prev, issueIds) : prev));
  }

  const handleThumbnailCached = useCallback(() => {
    setThumbCacheVersion((value) => value + 1);
  }, []);

  const { enqueue: enqueueFix, reset: resetFixQueue, clearBatchScope, fixStates } = useFixQueue(
    executeFix,
    (message) => setError(message)
  );

  useEffect(() => {
    fetchHistory().then(setHistory).catch(() => {});
  }, [result]);

  function resetFixState() {
    setOriginalPresentationId(null);
    setWorkingPresentationId(null);
    workingPresentationIdRef.current = null;
    setFixedPresentationUrl(null);
    setAppliedFixCount(0);
    resetFixQueue();
    clearThumbnailCache();
  }

  async function handleSlides(value?: string) {
    const target = (value ?? slidesUrl).trim();
    if (!target) return;
    setLoading(true);
    setError("");
    resetFixState();
    try {
      const data = await validateSlides(target);
      const enriched = enrichValidationResult(data);
      setResult(enriched);
      if (enriched.presentation_id) setOriginalPresentationId(enriched.presentation_id);
      if (enriched.working_presentation_id) {
        setWorkingPresentationId(enriched.working_presentation_id);
        workingPresentationIdRef.current = enriched.working_presentation_id;
        setFixedPresentationUrl(
          enriched.working_presentation_url || slidesEditUrl(enriched.working_presentation_id)
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al validar Slides");
    } finally {
      setLoading(false);
    }
  }

  async function handlePickFromDrive() {
    setError("");
    resetFixState();
    try {
      const config = await resolvePickerConfig();
      const picked = await openSlidesPicker(config);
      if (!picked) return;

      if (!isGoogleSlidesMime(picked.mimeType)) {
        setError(
          `El archivo «${picked.name}» no es una presentación de Google Slides (tipo detectado: ${describeMimeType(picked.mimeType)}).`
        );
        return;
      }

      setSlidesUrl(picked.id);
      setSelectedSlidesName(picked.name);
      await handleSlides(picked.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo abrir Google Drive");
    }
  }

  async function handleFix(
    issueIds: string[],
    scopeKey: string,
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) {
    setError("");
    enqueueFix(issueIds, scopeKey, options);
  }

  const canFix = result?.source_type === "google_slides" && !!(originalPresentationId || result.presentation_id);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <div className="badge">Validador · v2.1</div>
          <h1>Validador de Identidad</h1>
        </div>
        <div className="user-menu">
          <span>{user?.name || user?.email}</span>
          <button className="btn btn-ghost" onClick={logout}>Salir</button>
        </div>
      </header>

      <div className="upload-section">
        <p>Selecciona una presentación desde Google Drive o pega su URL manualmente.</p>
        <button
          className="btn btn-primary drive-picker-btn"
          onClick={handlePickFromDrive}
          disabled={loading}
        >
          {loading ? "Validando..." : "Seleccionar desde Drive"}
        </button>
        {selectedSlidesName && (
          <p className="selected-file">Archivo seleccionado: <strong>{selectedSlidesName}</strong></p>
        )}
        <div className="divider"><span>o</span></div>
        <input
          type="text"
          placeholder="https://docs.google.com/presentation/d/..."
          value={slidesUrl}
          onChange={(e) => {
            setSlidesUrl(e.target.value);
            setSelectedSlidesName("");
          }}
          disabled={loading}
        />
        <button className="btn btn-secondary" onClick={() => handleSlides()} disabled={loading || !slidesUrl.trim()}>
          Validar por URL
        </button>
          <p className="hint">Al validar se crea una copia de trabajo en Google Slides; las correcciones se aplican sobre ella sin modificar el original.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <ResultsView
          result={result}
          onEnqueueFix={handleFix}
          onDiscard={handleDiscard}
          onThumbnailCached={handleThumbnailCached}
          onClearBatchScope={clearBatchScope}
          fixStates={fixStates}
          canFix={canFix && !!workingPresentationId}
          originalPresentationId={originalPresentationId}
          workingPresentationId={workingPresentationId}
          appliedFixCount={appliedFixCount}
          fixedPresentationUrl={fixedPresentationUrl}
          thumbCacheVersion={thumbCacheVersion}
        />
      )}

      {history.length > 0 && (
        <section className="history-section">
          <h2>Historial reciente</h2>
          <ul>
            {history.map((item) => (
              <li key={item.id}>
                <button onClick={() => fetchValidation(item.id).then((data) => {
                  const enriched = enrichValidationResult(data);
                  setResult(enriched);
                  resetFixState();
                  if (enriched.presentation_id) setOriginalPresentationId(enriched.presentation_id);
                })}>
                  {item.source} — {item.passed ? "Conforme" : "Con incidencias"} — {new Date(item.created_at).toLocaleString()}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Cargando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
    </Routes>
  );
}
