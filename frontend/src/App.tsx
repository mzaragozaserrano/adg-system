import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Navigate, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import {
  buildLayout,
  downloadReportPdf,
  fetchHistory,
  fetchValidation,
  fixPresentation,
  googleLoginUrl,
  validateSlides,
} from "./api";
import {
  describeMimeType,
  isGoogleSlidesMime,
  isLayoutSourceMime,
  isPdfMime,
  openLayoutSourcePicker,
  openSlidesPicker,
} from "./googlePicker";
import { resolvePickerConfig } from "./pickerConfig";
import { useAuth } from "./auth";

import type { BulkPromptState, FixState, Issue, LayoutBuildResult, ValidationResult } from "./types";
import {
  buildColorOverridesForIssues,
  buildFixPayload,
  enrichValidationResult,
  fixButtonLabel,
  hasFixMetadata,
  paletteGroupKey,
  removeIssuesFromResult,
  similarIssueIds,
  slideSummary,
  slidesEditUrl,
} from "./utils/validationUtils";
import ColorPaletteCompare from "./components/ColorPaletteCompare";
import SimilarBulkDialog from "./components/SimilarBulkDialog";
import SlideThumbnail, {
  clearThumbnailCache,
  preloadSlideThumbnails,
} from "./components/SlideThumbnail";
import { useFixQueue } from "./features/validator/useFixQueue";

function LoginPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Cargando...</div>;
  if (user) return <Navigate to="/" replace />;

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="badge">ADG System · v2.1</div>
        <h1>ADG System</h1>
        <p>Accede con tu cuenta corporativa de Google para acceder a las herramientas de maquetación y validación.</p>
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
    const slideNums = Array.from(new Set(result.issues.map((issue) => issue.slide)));
    preloadSlideThumbnails(thumbPresentationId, slideNums, onThumbnailCached);
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

function ValidatorDashboard({ onBack }: { onBack?: () => void }) {
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
          {onBack && (
            <button className="btn btn-ghost btn-back" onClick={onBack}>← Inicio</button>
          )}
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

function MaquetadorDashboard({ onBack }: { onBack?: () => void }) {
  const { user, logout } = useAuth();
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceType, setSourceType] = useState<"slides" | "pdf">("slides");
  const [localPdfFile, setLocalPdfFile] = useState<File | null>(null);
  const [titleOverride, setTitleOverride] = useState("");
  const [subtitleOverride, setSubtitleOverride] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<LayoutBuildResult | null>(null);

  function clearSelection() {
    setSourceUrl("");
    setSourceName("");
    setSourceType("slides");
    setLocalPdfFile(null);
    setResult(null);
  }

  async function handlePickFromDrive() {
    setError("");
    try {
      const config = await resolvePickerConfig();
      const picked = await openLayoutSourcePicker(config);
      if (!picked) return;
      if (!isLayoutSourceMime(picked.mimeType)) {
        setError(
          `El archivo «${picked.name}» no es compatible (tipo detectado: ${describeMimeType(picked.mimeType)}). Usa Google Slides o PDF.`
        );
        return;
      }
      setSourceUrl(picked.id);
      setSourceName(picked.name);
      setSourceType(isPdfMime(picked.mimeType) ? "pdf" : "slides");
      setLocalPdfFile(null);
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo abrir Google Drive");
    }
  }

  function handleLocalPdfChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLocalPdfFile(file);
    setSourceName(file.name);
    setSourceType("pdf");
    setSourceUrl("local");
    setResult(null);
  }

  async function handleBuildLayout() {
    const hasSource = localPdfFile !== null || sourceUrl.trim().length > 0;
    if (!hasSource) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await buildLayout(
        localPdfFile ? "local" : sourceUrl.trim(),
        sourceType,
        sourceName || "Presentacion",
        titleOverride.trim(),
        subtitleOverride.trim(),
        localPdfFile ?? undefined,
      );
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al maquetar");
    } finally {
      setLoading(false);
    }
  }

  const hasSource = localPdfFile !== null || sourceUrl.trim().length > 0;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          {onBack && (
            <button className="btn btn-ghost btn-back" onClick={onBack}>← Inicio</button>
          )}
          <div className="badge">Maquetador · v1.0</div>
          <h1>Maquetador ADG</h1>
        </div>
        <div className="user-menu">
          <span>{user?.name || user?.email}</span>
          <button className="btn btn-ghost" onClick={logout}>Salir</button>
        </div>
      </header>

      <div className="upload-section">
        <p>
          Selecciona un PDF o una presentación de Google Slides del cliente. Se generará una maqueta
          nueva en tu Drive con portada, contraportada y textos extraídos según la identidad ADG.
        </p>
        <button className="btn btn-primary drive-picker-btn" onClick={handlePickFromDrive} disabled={loading}>
          Seleccionar desde Drive
        </button>
        <div className="divider"><span>o</span></div>
        <label className="btn btn-secondary" style={{ cursor: "pointer", display: "inline-block" }}>
          Subir PDF desde el equipo
          <input
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={handleLocalPdfChange}
            disabled={loading}
          />
        </label>
        {sourceName && (
          <p className="selected-file">
            Archivo seleccionado: <strong>{sourceName}</strong>{" "}
            ({sourceType === "pdf" ? "PDF" : "Google Slides"})
            {" "}<button className="btn btn-ghost btn-sm" onClick={clearSelection}>✕</button>
          </p>
        )}
        {!localPdfFile && (
          <>
            <div className="divider"><span>o pega la URL / ID</span></div>
            <input
              type="text"
              placeholder="https://docs.google.com/presentation/d/..."
              value={sourceUrl === "local" ? "" : sourceUrl}
              onChange={(e) => {
                setSourceUrl(e.target.value);
                setSourceName("");
                setSourceType("slides");
                setLocalPdfFile(null);
                setResult(null);
              }}
              disabled={loading}
            />
          </>
        )}
      </div>

      <div className="transcriber-config">
        <div className="transcriber-options">
          <h3>Opciones</h3>
          <label className="transcriber-toggle-row">
            <span>Título de portada (opcional)</span>
            <input
              type="text"
              value={titleOverride}
              onChange={(e) => setTitleOverride(e.target.value)}
              placeholder="Se detecta automáticamente si se deja vacío"
              disabled={loading}
            />
          </label>
          <label className="transcriber-toggle-row">
            <span>Subtítulo de portada (opcional)</span>
            <input
              type="text"
              value={subtitleOverride}
              onChange={(e) => setSubtitleOverride(e.target.value)}
              placeholder="Se detecta automáticamente si se deja vacío"
              disabled={loading}
            />
          </label>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleBuildLayout}
          disabled={loading || !hasSource}
        >
          {loading ? "Maquetando..." : "Maquetar presentación"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="transcriber-result">
          <h2>Resultado</h2>
          <p className="transcriber-result-ok">
            Maqueta generada con {result.slides_processed} diapositiva{result.slides_processed !== 1 ? "s" : ""}.
          </p>
          {result.cover_title && (
            <p>Título de portada: <strong>{result.cover_title}</strong></p>
          )}
          {result.cover_subtitle && (
            <p>Subtítulo de portada: <strong>{result.cover_subtitle}</strong></p>
          )}
          {result.skipped_slides.length > 0 && (
            <p className="hint">
              Diapositivas omitidas (sin texto detectado): {result.skipped_slides.join(", ")}
            </p>
          )}
          {result.presentation_url && (
            <a
              className="btn btn-primary"
              href={result.presentation_url}
              target="_blank"
              rel="noreferrer"
            >
              Abrir maqueta en Google Slides
            </a>
          )}
        </div>
      )}
    </div>
  );
}

type AppMode = "home" | "maquetador" | "validator";

function Dashboard() {
  const { user, logout } = useAuth();
  const [mode, setMode] = useState<AppMode>("home");

  if (mode === "maquetador") return <MaquetadorDashboard onBack={() => setMode("home")} />;
  if (mode === "validator") return <ValidatorDashboard onBack={() => setMode("home")} />;

  return (
    <div className="app home-page">
      <header className="app-header">
        <div>
          <div className="badge">ADG System · v2.1</div>
          <h1>ADG System</h1>
        </div>
        <div className="user-menu">
          <span>{user?.name || user?.email}</span>
          <button className="btn btn-ghost" onClick={logout}>Salir</button>
        </div>
      </header>
      <p className="home-subtitle">Selecciona una herramienta para continuar.</p>
      <div className="home-cards">
        <button className="home-card" onClick={() => setMode("maquetador")}>
          <div className="home-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18M9 21V9"/>
            </svg>
          </div>
          <div className="home-card-body">
            <h2>Maquetador</h2>
            <p>Genera una maqueta ADG a partir de un PDF o Google Slides del cliente, con textos extraídos y estructura corporativa.</p>
          </div>
        </button>
        <button className="home-card" onClick={() => setMode("validator")}>
          <div className="home-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 11l3 3L22 4"/>
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
            </svg>
          </div>
          <div className="home-card-body">
            <h2>Validador</h2>
            <p>Comprueba que una presentación de Google Slides cumple el manual de identidad corporativa ADG.</p>
          </div>
        </button>
      </div>
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
