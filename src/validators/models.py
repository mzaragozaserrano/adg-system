from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    GRAVE = "grave"
    POSIBLE = "posible"

    @property
    def label(self) -> str:
        return "ERROR GRAVE" if self == Severity.GRAVE else "POSIBLE ERROR"


@dataclass
class ValidationIssue:
    slide_number: int
    category: str
    message: str
    expected: str = ""
    actual: str = ""
    text_preview: str = ""
    element: str = ""
    location: str = ""
    severity: Severity = Severity.GRAVE
    object_id: str | None = None
    text_range: dict[str, int] | None = None
    fix_type: str | None = None
    fix_payload: dict[str, Any] | None = None
    issue_id: str | None = None
    color_actual: str | None = None
    color_suggested: str | None = None
    color_suggestions: list[dict[str, str]] | None = None

    @property
    def is_fixable(self) -> bool:
        return (
            self.fix_type is not None
            and self.fix_payload is not None
            and self.object_id is not None
        )

    def to_dict(self) -> dict:
        data = {
            "slide": self.slide_number,
            "category": self.category,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "text_preview": self.text_preview,
            "element": self.element,
            "location": self.location,
            "severity": self.severity.value,
            "severity_label": self.severity.label,
            "is_fixable": self.is_fixable,
        }
        if self.issue_id:
            data["issue_id"] = self.issue_id
        if self.object_id:
            data["object_id"] = self.object_id
        if self.text_range:
            data["text_range"] = self.text_range
        if self.fix_type:
            data["fix_type"] = self.fix_type
        if self.fix_payload:
            data["fix_payload"] = self.fix_payload
        if self.color_actual:
            data["color_actual"] = self.color_actual
        if self.color_suggested:
            data["color_suggested"] = self.color_suggested
        if self.color_suggestions:
            data["color_suggestions"] = self.color_suggestions
        return data


@dataclass
class ValidationResult:
    source: str
    source_type: str
    total_slides: int
    issues: list[ValidationIssue] = field(default_factory=list)
    presentation_id: str | None = None
    validation_id: str | None = None

    @property
    def passed(self) -> bool:
        return self.grave_count == 0

    @property
    def grave_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.GRAVE)

    @property
    def posible_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.POSIBLE)

    @property
    def fixable_count(self) -> int:
        return sum(1 for i in self.issues if i.is_fixable)

    @property
    def error_count(self) -> int:
        return self.grave_count

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "total_slides": self.total_slides,
            "passed": self.passed,
            "grave_count": self.grave_count,
            "posible_count": self.posible_count,
            "fixable_count": self.fixable_count,
            "presentation_id": self.presentation_id,
            "validation_id": self.validation_id,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class FixResult:
    source_presentation_id: str
    fixed_presentation_id: str
    fixed_url: str
    fixes_applied: int
    issue_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_presentation_id": self.source_presentation_id,
            "fixed_presentation_id": self.fixed_presentation_id,
            "fixed_url": self.fixed_url,
            "fixes_applied": self.fixes_applied,
            "issue_ids": self.issue_ids,
        }
