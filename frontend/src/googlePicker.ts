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

export async function openSlidesPicker(config: PickerConfig): Promise<PickerFile | null> {
  await ensurePickerApi();
  const google = (window as any).google;
  if (!google?.picker) throw new Error("Google Picker no disponible");

  return new Promise((resolve, reject) => {
    try {
      const view = new google.picker.DocsView(google.picker.ViewId.PRESENTATIONS)
        .setIncludeFolders(false)
        .setMimeTypes(SLIDES_MIME)
        .setSelectFolderEnabled(false);

      const picker = new google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(config.access_token)
        .setDeveloperKey(config.api_key)
        .setAppId(config.app_id)
        .setTitle("Seleccionar presentación de Google Slides")
        .setCallback((data: any) => {
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
