const API_BASE = import.meta.env.VITE_API_URL || "/api";

export function getToken(): string | null {
  return localStorage.getItem("adg_token");
}

export function setToken(token: string) {
  localStorage.setItem("adg_token", token);
}

export function clearToken() {
  localStorage.removeItem("adg_token");
}

async function apiFetch(path: string, options: RequestInit = {}, retries = 2) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) {
      await new Promise((res) => setTimeout(res, attempt * 1500));
    }
    let response: Response;
    try {
      response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch {
      if (attempt < retries) continue;
      const isWrite = options.method && options.method.toUpperCase() !== "GET";
      throw new Error(
        isWrite
          ? "No se pudo conectar con el servidor. Comprueba tu conexión y vuelve a intentarlo."
          : "El servidor no está disponible. Espera un momento y vuelve a intentar."
      );
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      const detail = body?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join("; ")
            : JSON.stringify(body);
      throw new Error(message || `Error de API (${response.status})`);
    }
    return response;
  }
  throw new Error("El servidor no está disponible. Espera un momento y vuelve a intentar.");
}

export async function wakeApi() {
  try {
    await fetch(`${API_BASE}/health`);
  } catch {
    // warm-up silencioso: si falla no pasa nada
  }
}

export async function fetchMe() {
  const response = await apiFetch("/auth/me");
  return response.json();
}

export async function validatePdf(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await apiFetch("/presentations/validate/pdf", {
    method: "POST",
    body: form,
  });
  return response.json();
}

export async function fetchPickerConfig() {
  const response = await apiFetch("/auth/google/picker-config");
  return response.json();
}

export async function validateSlides(urlOrId: string) {
  const response = await apiFetch("/presentations/validate/slides", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url_or_id: urlOrId }),
  });
  return response.json();
}

export interface FixIssuePayload {
  issue_id: string;
  object_id: string;
  fix_type: string;
  fix_payload: Record<string, unknown>;
  text_range?: { start: number; end: number };
}

export async function fixPresentation(
  presentationId: string,
  issues: FixIssuePayload[],
  originalPresentationId: string,
  mode: "copy" | "in_place" = "in_place"
) {
  const response = await apiFetch("/presentations/fix", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      presentation_id: presentationId,
      original_presentation_id: originalPresentationId,
      issue_ids: issues.map((issue) => issue.issue_id),
      issues,
      mode,
    }),
  }, 0);
  return response.json();
}

export async function fetchHistory() {
  const response = await apiFetch("/presentations/history");
  return response.json();
}

export async function fetchValidation(id: number) {
  const response = await apiFetch(`/presentations/history/${id}`);
  return response.json();
}

export async function logoutSession(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    // aunque falle en red el token local se elimina igualmente
  }
}

export function googleLoginUrl() {
  return `${API_BASE}/auth/google`;
}

export function reportPdfUrl(validationId: string) {
  return `${API_BASE}/presentations/history/${validationId}/report.pdf`;
}

export async function downloadReportPdf(validationId: string) {
  const response = await apiFetch(`/presentations/history/${validationId}/report.pdf`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `informe_validacion_${validationId}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function fetchThumbnail(presentationId: string, slideNumber: number): Promise<string> {
  const response = await apiFetch(`/presentations/slides/${presentationId}/thumbnail/${slideNumber}`);
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function buildLayout(
  urlOrId: string,
  sourceType: "slides" | "pdf",
  filename: string,
  titleOverride = "",
  subtitleOverride = "",
  pdfFile?: File,
) {
  const form = new FormData();
  form.append("url_or_id", urlOrId || "local");
  form.append("source_type", sourceType);
  form.append("filename", filename);
  form.append("title_override", titleOverride);
  form.append("subtitle_override", subtitleOverride);
  if (pdfFile) {
    form.append("pdf_file", pdfFile);
  }
  const response = await apiFetch("/layout/build", {
    method: "POST",
    body: form,
  });
  return response.json();
}

export async function transcribeSlides(
  urlOrId: string,
  slideNumbers: number[],
  newDocument: boolean
) {
  const response = await apiFetch("/transcriber/transcribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url_or_id: urlOrId,
      slide_numbers: slideNumbers,
      new_document: newDocument,
    }),
  });
  return response.json();
}

export async function exportPresentation(presentationId: string, format: "pdf" | "pptx") {
  const response = await apiFetch("/presentations/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ presentation_id: presentationId, format }),
  });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `presentacion.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}
