const CATEGORY_LABELS: Record<string, string> = {
  color: "Color",
  tipografía: "Tipografía",
  peso_fuente: "Peso de fuente",
  tamaño: "Tamaño de texto",
  numeración: "Numeración",
  formato: "Formato",
  fondo: "Fondo de diapositiva",
  forma: "Forma",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category.replace(/_/g, " ");
}

export function severityLabel(severity: string, fallback = ""): string {
  if (severity === "grave") return "Error grave";
  if (severity === "posible") return "Posible error";
  return fallback;
}
