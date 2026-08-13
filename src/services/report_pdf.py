from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config.settings import settings


def generate_report_pdf(result: dict, validation_id: int) -> Path:
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = settings.exports_dir / f"informe_validacion_{validation_id}.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ADGTitle",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#02445B"),
        spaceAfter=12,
    )
    body_style = styles["Normal"]
    story = []

    story.append(Paragraph("Informe de Validación ADG", title_style))
    story.append(Paragraph(f"Fuente: {result.get('source', '')}", body_style))
    story.append(Paragraph(f"Tipo: {result.get('source_type', '')}", body_style))
    story.append(
        Paragraph(
            f"Diapositivas: {result.get('total_slides', 0)} | "
            f"Graves: {result.get('grave_count', 0)} | "
            f"Posibles: {result.get('posible_count', 0)}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    table_data = [["Diap.", "Severidad", "Categoría", "Mensaje", "Esperado", "Actual"]]
    for issue in result.get("issues", []):
        table_data.append(
            [
                str(issue.get("slide", "")),
                issue.get("severity_label", ""),
                issue.get("category", ""),
                issue.get("message", "")[:60],
                issue.get("expected", "")[:40],
                issue.get("actual", "")[:40],
            ]
        )

    table = Table(table_data, repeatRows=1, colWidths=[1.2 * cm, 2.5 * cm, 2.5 * cm, 5 * cm, 3 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#02445B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return pdf_path
