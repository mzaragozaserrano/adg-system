from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None


class SlidesValidateRequest(BaseModel):
    url_or_id: str = Field(..., min_length=5)


class IssueFixInput(BaseModel):
    issue_id: str
    object_id: str
    fix_type: str
    fix_payload: dict
    text_range: dict[str, int] | None = None


class FixRequest(BaseModel):
    presentation_id: str
    original_presentation_id: str
    issue_ids: list[str] = Field(..., min_length=1)
    issues: list[IssueFixInput] = Field(..., min_length=1)
    mode: str = "in_place"


class ExportRequest(BaseModel):
    presentation_id: str
    format: str = "pdf"


class ValidationHistoryItem(BaseModel):
    id: int
    source: str
    source_type: str
    total_slides: int
    grave_count: int
    posible_count: int
    passed: bool
    created_at: str


class TranscribeRequest(BaseModel):
    url_or_id: str = Field(..., min_length=5)
    slide_numbers: list[int] = Field(..., min_length=1)
    new_document: bool = False


class LayoutBuildRequest(BaseModel):
    url_or_id: str = Field(..., min_length=5)
    source_type: str = Field("slides", pattern="^(slides|pdf)$")
    filename: str = Field("Presentacion", min_length=1)
    title_override: str = ""
    subtitle_override: str = ""


class LayoutBuildResponse(BaseModel):
    presentation_url: str
    presentation_id: str
    slides_processed: int
    skipped_slides: list[int]
    cover_title: str
    cover_subtitle: str
