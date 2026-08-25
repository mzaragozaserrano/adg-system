export interface Issue {
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

export interface ValidationResult {
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

export type FixState = "idle" | "fixing" | "fixed" | "error";

export type BulkAction = "fix" | "discard";

export interface BulkPromptState {
  action: BulkAction;
  anchor: Issue;
  similarIds: string[];
  currentIds?: string[];
  matchCount?: number;
  problemsLabel?: string;
}

export interface LayoutBuildResult {
  presentation_url: string;
  presentation_id: string;
  slides_processed: number;
  skipped_slides: number[];
  cover_title: string;
  cover_subtitle: string;
}

export interface TranscribeResult {
  slides: Array<{
    slide_number: number;
    images_found: number;
    images_processed: number;
    texts_extracted: string[];
    skipped?: boolean;
    error?: string;
  }>;
  total_images: number;
  total_texts: number;
  document_url?: string;
}
