export interface PickerConfig {
  access_token: string;
  api_key: string;
  app_id: string;
  client_id: string;
}

export interface PickerFile {
  id: string;
  name: string;
  mimeType: string;
}

const SLIDES_MIME = "application/vnd.google-apps.presentation";

const MIME_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.google-apps.document": "Google Docs",
  "application/vnd.google-apps.spreadsheet": "Google Sheets",
  "application/vnd.google-apps.form": "Google Forms",
};

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.body.appendChild(script);
  });
}

async function ensurePickerApi(): Promise<void> {
  await loadScript("https://apis.google.com/js/api.js");
  const gapi = (window as any).gapi;
  if (!gapi) throw new Error("Google API no disponible");
  await new Promise<void>((resolve) => gapi.load("picker", { callback: resolve }));
}

export function describeMimeType(mimeType: string): string {
  return MIME_LABELS[mimeType] || mimeType || "desconocido";
}

export function isGoogleSlidesMime(mimeType: string): boolean {
  return mimeType === SLIDES_MIME;
}

export function isPdfMime(mimeType: string): boolean {
  return mimeType === "application/pdf";
}

export function isLayoutSourceMime(mimeType: string): boolean {
  return isGoogleSlidesMime(mimeType) || isPdfMime(mimeType);
}

export async function openLayoutSourcePicker(config: PickerConfig): Promise<PickerFile | null> {
  await ensurePickerApi();
  const google = (window as any).google;
  if (!google?.picker) throw new Error("Google Picker no disponible");

  if (!config.api_key?.trim()) {
    throw new Error("Falta la API key del Picker (VITE_GOOGLE_API_KEY).");
  }

  return new Promise((resolve, reject) => {
    try {
      const slidesView = new google.picker.DocsView(google.picker.ViewId.PRESENTATIONS)
        .setIncludeFolders(false)
        .setMimeTypes(SLIDES_MIME)
        .setSelectFolderEnabled(false);

      const pdfView = new google.picker.DocsView()
        .setIncludeFolders(false)
        .setMimeTypes("application/pdf")
        .setSelectFolderEnabled(false);

      const picker = new google.picker.PickerBuilder()
        .addView(slidesView)
        .addView(pdfView)
        .setOAuthToken(config.access_token)
        .setDeveloperKey(config.api_key.trim())
        .setAppId(config.app_id.trim())
        .setOrigin(getPickerOrigin())
        .setTitle("Seleccionar presentación o PDF")
        .setCallback((data: any) => {
          if (data[google.picker.Response.ERROR]) {
            const code = data[google.picker.Response.ERROR];
            if (code === "developerKeyInvalid" || String(code).toLowerCase().includes("developer")) {
              reject(
                new Error(
                  "La API key de Google Picker no es válida para este dominio. " +
                    "Usa una key tipo «Aplicación web» con referrer " +
                    `${getPickerOrigin()}/* y habilita Google Picker API en GCP.`
                )
              );
              return;
            }
            reject(new Error(`Error de Google Picker: ${code}`));
            return;
          }
          if (data.action === google.picker.Action.PICKED && data.docs?.[0]) {
            const doc = data.docs[0];
            resolve({
              id: doc.id,
              name: doc.name,
              mimeType: doc.mimeType,
            });
            return;
          }
          if (data.action === google.picker.Action.CANCEL) {
            resolve(null);
          }
        })
        .build();

      picker.setVisible(true);
    } catch (error) {
      reject(error);
    }
  });
}

function getPickerOrigin(): string {
  return `${window.location.protocol}//${window.location.host}`;
}

export async function openSlidesPicker(config: PickerConfig): Promise<PickerFile | null> {
  await ensurePickerApi();
  const google = (window as any).google;
  if (!google?.picker) throw new Error("Google Picker no disponible");

  if (!config.api_key?.trim()) {
    throw new Error("Falta la API key del Picker (VITE_GOOGLE_API_KEY).");
  }

  return new Promise((resolve, reject) => {
    try {
      const view = new google.picker.DocsView(google.picker.ViewId.PRESENTATIONS)
        .setIncludeFolders(false)
        .setMimeTypes(SLIDES_MIME)
        .setSelectFolderEnabled(false);

      const picker = new google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(config.access_token)
        .setDeveloperKey(config.api_key.trim())
        .setAppId(config.app_id.trim())
        .setOrigin(getPickerOrigin())
        .setTitle("Seleccionar presentación de Google Slides")
        .setCallback((data: any) => {
          if (data[google.picker.Response.ERROR]) {
            const code = data[google.picker.Response.ERROR];
            if (code === "developerKeyInvalid" || String(code).toLowerCase().includes("developer")) {
              reject(
                new Error(
                  "La API key de Google Picker no es válida para este dominio. " +
                    "Usa una key tipo «Aplicación web» con referrer " +
                    `${getPickerOrigin()}/* y habilita Google Picker API en GCP.`
                )
              );
              return;
            }
            reject(new Error(`Error de Google Picker: ${code}`));
            return;
          }
          if (data.action === google.picker.Action.PICKED && data.docs?.[0]) {
            const doc = data.docs[0];
            resolve({
              id: doc.id,
              name: doc.name,
              mimeType: doc.mimeType,
            });
            return;
          }
          if (data.action === google.picker.Action.CANCEL) {
            resolve(null);
          }
        })
        .build();

      picker.setVisible(true);
    } catch (error) {
      reject(error);
    }
  });
}
