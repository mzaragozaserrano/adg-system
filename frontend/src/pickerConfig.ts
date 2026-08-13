import { fetchPickerConfig } from "./api";
import type { PickerConfig } from "./googlePicker";

function trim(value: string | undefined): string {
  return (value || "").trim();
}

function buildPickerConfigError(): string {
  const origin = typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.host}`
    : "tu dominio";

  return (
    "Google Picker no configurado para este dominio. " +
    "En Vercel define VITE_GOOGLE_API_KEY y VITE_GOOGLE_APP_ID. " +
    "En Google Cloud, la API key debe ser tipo «Aplicación web» con restricción HTTP referrer " +
    `incluyendo ${origin}/* y habilitar Google Picker API.`
  );
}

export async function resolvePickerConfig(): Promise<PickerConfig> {
  const apiConfig = await fetchPickerConfig();

  const apiKey = trim(import.meta.env.VITE_GOOGLE_API_KEY) || trim(apiConfig.api_key);
  const appId = trim(import.meta.env.VITE_GOOGLE_APP_ID) || trim(apiConfig.app_id);

  if (!apiKey || !appId) {
    throw new Error(buildPickerConfigError());
  }

  if (!apiConfig.access_token) {
    throw new Error("No se pudo obtener el token de Google. Vuelve a iniciar sesión.");
  }

  return {
    access_token: apiConfig.access_token,
    api_key: apiKey,
    app_id: appId,
    client_id: trim(apiConfig.client_id),
  };
}
