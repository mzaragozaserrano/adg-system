import html
import json
import tempfile
from collections import defaultdict
from pathlib import Path

import streamlit as st

from config.brand_guidelines import (
    BRAND_FONT,
    SECTION_NUMBER_FONT_SIZE,
    SECTION_SUBTITLE_FONT_SIZE,
    SECTION_TITLE_FONT_SIZE,
    SUBTITLE_FONT_SIZE,
    TITLE_FONT_SIZE,
)
from config.settings import settings
from src.validators import validate_pdf
from src.validators.models import Severity, ValidationResult
from ui.styles import ADG_CSS

st.set_page_config(
    page_title="Validador ADG",
    page_icon="✓",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(ADG_CSS, unsafe_allow_html=True)

SEVERITY_OPTIONS = ["ERROR GRAVE", "POSIBLE ERROR"]
CATEGORY_PILLS_KEY = "filter_categories_pills"
SEVERITY_PILLS_KEY = "filter_severity_pills"


def init_session_state() -> None:
    if "validation_result" not in st.session_state:
        st.session_state.validation_result = None


def render_hero() -> None:
    st.markdown(
        """<div class="app-hero">
            <div class="badge">Validador · v1.0</div>
            <h1>Validador de Identidad</h1>
            <p>Comprueba tipografía, colores y estilo corporativo en presentaciones PDF</p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_stats(result: ValidationResult) -> None:
    categories = len({i.category for i in result.issues})
    st.markdown(
        f"""<div class="stat-grid">
            <div class="stat-box">
                <div class="number">{result.total_slides}</div>
                <div class="label">Diapositivas</div>
            </div>
            <div class="stat-box">
                <div class="number">{result.grave_count}</div>
                <div class="label">Errores graves</div>
            </div>
            <div class="stat-box">
                <div class="number">{result.posible_count}</div>
                <div class="label">Posibles errores</div>
            </div>
            <div class="stat-box">
                <div class="number">{categories}</div>
                <div class="label">Tipos</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_issue(issue: dict, index: int) -> None:
    severity = issue.get("severity", "grave")
    is_grave = severity == Severity.GRAVE.value
    card_class = "issue-card issue-card--grave" if is_grave else "issue-card issue-card--posible"
    label = html.escape(issue.get("severity_label", "ERROR GRAVE"))
    category = html.escape(issue.get("category", ""))
    message = html.escape(issue.get("message", ""))

    element = issue.get("element") or issue.get("text_preview")
    element_html = ""
    if element:
        element_html = (
            f'<div class="issue-meta-row">'
            f'<span class="issue-meta-label">Elemento</span>'
            f'<span class="issue-meta-value">{html.escape(element)}</span>'
            f"</div>"
        )

    location_html = ""
    if issue.get("location"):
        location_html = (
            f'<div class="issue-meta-row">'
            f'<span class="issue-meta-label">Ubicación</span>'
            f'<span class="issue-meta-value">{html.escape(issue["location"])}</span>'
            f"</div>"
        )

    st.markdown(
        f"""<div class="{card_class}">
            <div class="issue-card-header">
                <span class="issue-index">#{index}</span>
                <span class="issue-severity">{label}</span>
                <span class="issue-cat">{category}</span>
            </div>
            <div class="issue-msg">{message}</div>
            {element_html}
            {location_html}
        </div>""",
        unsafe_allow_html=True,
    )

    col_expected, col_actual = st.columns(2)
    with col_expected:
        st.markdown(
            f'<div class="issue-compare-item">'
            f'<span class="issue-compare-label">Esperado</span>'
            f'<span class="issue-compare-value">{html.escape(issue.get("expected", ""))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_actual:
        actual_class = "issue-compare-item issue-compare-item--actual"
        if not is_grave:
            actual_class += " issue-compare-item--actual-posible"
        st.markdown(
            f'<div class="{actual_class}">'
            f'<span class="issue-compare-label">Actual</span>'
            f'<span class="issue-compare-value">{html.escape(issue.get("actual", ""))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def reset_filters(category_counts: dict[str, int]) -> None:
    category_options = [
        category_label(cat, category_counts[cat])
        for cat in sorted(category_counts.keys())
    ]
    st.session_state[SEVERITY_PILLS_KEY] = list(SEVERITY_OPTIONS)
    st.session_state[CATEGORY_PILLS_KEY] = list(category_options)


def category_label(category: str, count: int) -> str:
    return f"{category} ({count})"


def parse_category_label(label: str) -> str:
    if " (" in label:
        return label.rsplit(" (", 1)[0]
    return label


def filter_issues(
    issues: list[dict],
    severities: list[str] | None,
    categories: list[str] | None,
) -> list[dict]:
    if not severities or not categories:
        return []

    severity_keys: list[str] = []
    if "ERROR GRAVE" in severities:
        severity_keys.append(Severity.GRAVE.value)
    if "POSIBLE ERROR" in severities:
        severity_keys.append(Severity.POSIBLE.value)

    category_keys = {parse_category_label(label) for label in categories}

    return [
        issue
        for issue in issues
        if issue.get("severity") in severity_keys
        and issue.get("category") in category_keys
    ]


@st.fragment
def render_filters_and_issues(all_issues: list[dict]) -> None:
    category_counts: dict[str, int] = defaultdict(int)
    for issue in all_issues:
        category_counts[issue["category"]] += 1

    category_options = [
        category_label(cat, category_counts[cat])
        for cat in sorted(category_counts.keys())
    ]
    category_option_set = set(category_options)

    if SEVERITY_PILLS_KEY not in st.session_state:
        st.session_state[SEVERITY_PILLS_KEY] = list(SEVERITY_OPTIONS)
    else:
        stored = st.session_state[SEVERITY_PILLS_KEY] or []
        st.session_state[SEVERITY_PILLS_KEY] = [
            item for item in stored if item in SEVERITY_OPTIONS
        ]
        if not st.session_state[SEVERITY_PILLS_KEY]:
            st.session_state[SEVERITY_PILLS_KEY] = list(SEVERITY_OPTIONS)

    if CATEGORY_PILLS_KEY not in st.session_state:
        st.session_state[CATEGORY_PILLS_KEY] = list(category_options)
    else:
        stored = st.session_state[CATEGORY_PILLS_KEY] or []
        valid = [item for item in stored if item in category_option_set]
        st.session_state[CATEGORY_PILLS_KEY] = valid or list(category_options)

    with st.container(border=True):
        st.markdown("### Filtros")

        action_col1, action_col2, _ = st.columns([1, 1, 2])
        with action_col1:
            if st.button("Marcar todos", key="filter_select_all", use_container_width=True):
                st.session_state[SEVERITY_PILLS_KEY] = list(SEVERITY_OPTIONS)
                st.session_state[CATEGORY_PILLS_KEY] = list(category_options)
                st.rerun(scope="fragment")
        with action_col2:
            if st.button("Desmarcar todos", key="filter_clear_all", use_container_width=True):
                st.session_state[SEVERITY_PILLS_KEY] = []
                st.session_state[CATEGORY_PILLS_KEY] = []
                st.rerun(scope="fragment")

        severity_selected = st.pills(
            "Severidad",
            options=SEVERITY_OPTIONS,
            selection_mode="multi",
            key=SEVERITY_PILLS_KEY,
        )
        categories_selected = st.pills(
            "Categoría",
            options=category_options,
            selection_mode="multi",
            key=CATEGORY_PILLS_KEY,
        )

    severity_list = list(severity_selected or [])
    categories_list = list(categories_selected or [])
    filtered = filter_issues(all_issues, severity_list, categories_list)
    slide_count = len({issue["slide"] for issue in filtered})
    total = len(all_issues)
    active_filters = len(severity_list) + len(categories_list)
    max_filters = len(SEVERITY_OPTIONS) + len(category_options)

    if not severity_list or not categories_list:
        st.warning("Selecciona al menos una severidad y una categoría para ver resultados.")
        st.caption(
            f"Activos: {len(severity_list)}/{len(SEVERITY_OPTIONS)} severidades · "
            f"{len(categories_list)}/{len(category_options)} categorías"
        )
        return

    st.markdown(
        f'<div class="filter-summary">'
        f'Mostrando <strong>{len(filtered)}</strong> de <strong>{total}</strong> errores '
        f'en <strong>{slide_count}</strong> diapositiva(s) · '
        f'Filtros activos: <strong>{active_filters}/{max_filters}</strong>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("No hay errores con los filtros seleccionados.")
        return

    by_slide: dict[int, list] = defaultdict(list)
    for issue in filtered:
        by_slide[issue["slide"]].append(issue)

    slide_nums = sorted(by_slide.keys())
    for i, slide_num in enumerate(slide_nums):
        slide_issues = by_slide[slide_num]
        graves = sum(1 for x in slide_issues if x.get("severity") == Severity.GRAVE.value)
        posibles = len(slide_issues) - graves
        detail = f"{graves} grave(s)" + (f", {posibles} posible(s)" if posibles else "")
        label = f"Diapositiva {slide_num} — {detail}"
        with st.expander(label, expanded=(i == 0)):
            for j, issue in enumerate(slide_issues, 1):
                render_issue(issue, index=j)


def render_results(result: ValidationResult) -> None:
    render_stats(result)

    if not result.issues:
        st.markdown(
            f"""<div class="result-pass">
                <strong>Presentación conforme</strong><br>
                Las {result.total_slides} diapositivas cumplen el manual de identidad ADG.
            </div>""",
            unsafe_allow_html=True,
        )
        return

    if result.passed and result.posible_count > 0:
        st.markdown(
            f"""<div class="result-pass">
                <strong>Sin errores graves</strong><br>
                Se detectaron {result.posible_count} posible(s) aviso(s) a revisar.
            </div>""",
            unsafe_allow_html=True,
        )
    elif not result.passed:
        st.markdown(
            f"""<div class="result-fail">
                <strong>{result.grave_count} error(es) grave(s)</strong>
                {f" y {result.posible_count} posible(s)" if result.posible_count else ""}
            </div>""",
            unsafe_allow_html=True,
        )

    all_issues = [i.to_dict() for i in result.issues]

    render_filters_and_issues(all_issues)

    st.markdown(
        '<div class="download-section"><p>Exportar resultados del análisis</p></div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Descargar informe (JSON)",
        data=json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        file_name="informe_validacion_adg.json",
        mime="application/json",
        use_container_width=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### Reglas de validación")
        st.markdown(
            f"""
            **Tipografía general**  
            {BRAND_FONT} en todo el documento

            **Títulos** (superior izquierda, fuera de cuadros)  
            {BRAND_FONT} Bold · Petrol Blue · tamaño {TITLE_FONT_SIZE}

            **Subtítulos** (superior izquierda, fuera de cuadros)  
            {BRAND_FONT} Light · Obsidian Blue · tamaño {SUBTITLE_FONT_SIZE}

            **Diapositivas de sección**  
            Número · tamaño {SECTION_NUMBER_FONT_SIZE}  
            Título · tamaño {SECTION_TITLE_FONT_SIZE}  
            Subtítulo (opcional) · MAYÚSCULAS · tamaño {SECTION_SUBTITLE_FONT_SIZE}  
            Numeración consecutiva sin saltos ni repeticiones

            **Tamaño ±10 pt**  
            Diferencia mayor → Posible error (amarillo)  
            Diferencia menor → Error grave (rojo)

            ---

            **Colores**  
            Todos los elementos deben usar la paleta ADG
            """
        )
        st.markdown("---")
        st.caption("v1.0 · Validación local PDF")


init_session_state()
render_hero()
render_sidebar()

st.markdown('<div class="app-card">', unsafe_allow_html=True)
st.markdown("<h3>Subir presentación PDF</h3>", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Arrastra o selecciona un archivo PDF",
    type=["pdf"],
    label_visibility="collapsed",
)

validate = st.button("Validar presentación", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if validate:
    pdf_path: Path | None = None
    temp_file: Path | None = None

    try:
        if uploaded:
            settings.uploads_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", dir=settings.uploads_dir
            ) as tmp:
                tmp.write(uploaded.getvalue())
                temp_file = Path(tmp.name)
                pdf_path = temp_file
        else:
            st.warning("Selecciona un archivo PDF para validar.")
            st.stop()

        with st.spinner("Analizando presentación..."):
            result = validate_pdf(pdf_path)

        st.session_state.validation_result = result
        category_counts: dict[str, int] = defaultdict(int)
        for issue in result.issues:
            category_counts[issue.category] += 1
        reset_filters(category_counts)

    except Exception as e:
        st.error(f"Error al validar: {e}")
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink(missing_ok=True)

if st.session_state.validation_result is not None:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    render_results(st.session_state.validation_result)
    st.markdown("</div>", unsafe_allow_html=True)
