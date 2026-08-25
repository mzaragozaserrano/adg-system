import { ADG_PALETTE_OPTIONS } from "../constants/brandPalette";
import type { FixState, Issue, ValidationResult } from "../types";
import { categoryLabel } from "./issueLabels";

export function hasFixMetadata(issue: Issue): boolean {
  return Boolean(issue.fix_type && issue.object_id && issue.fix_payload);
}

export function enrichValidationResult(data: ValidationResult): ValidationResult {
  const pid = data.presentation_id || "doc";
  const issues = data.issues.map((issue, index) => {
    const enriched: Issue = {
      ...issue,
      issue_id: issue.issue_id || `${pid}-${issue.slide}-idx${index}-${issue.category}`,
    };
    return { ...enriched, is_fixable: hasFixMetadata(enriched) };
  });
  const fixable_count = issues.filter((i) => i.is_fixable).length;
  const grave_count = issues.filter((i) => i.severity === "grave").length;
  const posible_count = issues.filter((i) => i.severity === "posible").length;
  return { ...data, issues, fixable_count, grave_count, posible_count, passed: grave_count === 0 };
}

export function removeIssuesFromResult(result: ValidationResult, issueIds: string[]): ValidationResult {
  const fixed = new Set(issueIds);
  const issues = result.issues.filter((issue) => !issue.issue_id || !fixed.has(issue.issue_id));
  const grave_count = issues.filter((i) => i.severity === "grave").length;
  const posible_count = issues.filter((i) => i.severity === "posible").length;
  const fixable_count = issues.filter((i) => i.is_fixable).length;
  return { ...result, issues, grave_count, posible_count, fixable_count, passed: grave_count === 0 };
}

export function buildFixPayload(issue: Issue, colorOverride?: string) {
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

export function paletteGroupKey(issue: Issue): string | null {
  if (!issue.color_actual) return null;
  return `${issue.slide}:${issue.color_actual.toUpperCase()}`;
}

export function issueTextGroupKey(issue: Issue): string {
  if (issue.object_id && issue.text_range) {
    return `${issue.object_id}:${issue.text_range.start}:${issue.text_range.end}`;
  }
  if (issue.object_id && issue.text_preview) {
    return `${issue.object_id}:${issue.text_preview}`;
  }
  if (issue.text_preview) {
    return `preview:${issue.slide}:${issue.text_preview}`;
  }
  if (issue.object_id) {
    return `object:${issue.object_id}`;
  }
  return issue.issue_id || `${issue.slide}:${issue.category}:${issue.message}:${issue.actual}`;
}

export function groupIssuesByText(issues: Issue[]): Issue[][] {
  const groups = new Map<string, Issue[]>();
  const order: string[] = [];
  for (const issue of issues) {
    const key = issueTextGroupKey(issue);
    const existing = groups.get(key);
    if (existing) {
      existing.push(issue);
      continue;
    }
    groups.set(key, [issue]);
    order.push(key);
  }
  return order.map((key) => groups.get(key)!);
}

export function issueProblemKey(issue: Issue): string {
  return `${issue.category}::${issue.actual}`;
}

export function textGroupSignature(group: Issue[]): string {
  return group.map(issueProblemKey).sort().join("|");
}

export function describeTextGroupProblems(group: Issue[]): string {
  return [...group]
    .sort((a, b) => issueProblemKey(a).localeCompare(issueProblemKey(b)))
    .map((issue) => `${categoryLabel(issue.category)} «${issue.actual}»`)
    .join(", ");
}

export function collectGroupIssueIds(group: Issue[], fixableOnly = false): string[] {
  return group
    .filter((issue) => issue.issue_id && (!fixableOnly || hasFixMetadata(issue)))
    .map((issue) => issue.issue_id!);
}

export function similarTextGroups(
  issues: Issue[],
  anchorGroup: Issue[],
  fixableOnly = false
): { currentIds: string[]; similarIds: string[]; matchCount: number } {
  const slide = anchorGroup[0]?.slide;
  const signature = textGroupSignature(anchorGroup);
  const currentIds = collectGroupIssueIds(anchorGroup, fixableOnly);
  if (!slide || !signature || currentIds.length === 0) {
    return { currentIds, similarIds: currentIds, matchCount: currentIds.length > 0 ? 1 : 0 };
  }

  const matching = groupIssuesByText(issues.filter((issue) => issue.slide === slide))
    .filter((group) => textGroupSignature(group) === signature)
    .filter((group) => collectGroupIssueIds(group, fixableOnly).length > 0);

  return {
    currentIds,
    similarIds: matching.flatMap((group) => collectGroupIssueIds(group, fixableOnly)),
    matchCount: matching.length,
  };
}

export function similarIssueIds(issues: Issue[], anchor: Issue, fixableOnly = false): string[] {
  return issues
    .filter(
      (issue) =>
        issue.issue_id
        && issue.slide === anchor.slide
        && issue.category === anchor.category
        && issue.actual === anchor.actual
        && (!fixableOnly || hasFixMetadata(issue))
    )
    .map((issue) => issue.issue_id!);
}

export function buildColorOverridesForIssues(
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
      ? paletteSelections[key] || issue.color_suggested || ADG_PALETTE_OPTIONS[0]?.color
      : issue.color_suggested;
    if (color) overrides[issueId] = color;
  }
  return Object.keys(overrides).length > 0 ? overrides : undefined;
}

export function slidesEditUrl(presentationId: string): string {
  return `https://docs.google.com/presentation/d/${presentationId}/edit`;
}

export function slideSummary(issues: Issue[]): string {
  const graves = issues.filter((i) => i.severity === "grave").length;
  const posibles = issues.filter((i) => i.severity === "posible").length;
  const parts = [`${issues.length} error(es)`];
  if (graves) parts.push(`${graves} grave(s)`);
  if (posibles) parts.push(`${posibles} posible(s)`);
  return parts.join(" · ");
}

export function fixButtonLabel(state: FixState, defaultLabel: string): string {
  if (state === "fixing") return "Corrigiendo...";
  if (state === "fixed") return "Corregido";
  if (state === "error") return "Reintentar";
  return defaultLabel;
}

export function shortenError(message: string): string {
  const trimmed = message.trim();
  if (trimmed.length <= 280) return trimmed;
  return `${trimmed.slice(0, 277)}...`;
}
