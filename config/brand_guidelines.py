REFERENCE_MANUAL = "docs/reference/manual_identidad_corporativa.pdf"

BRAND_FONT = "Helvetica Neue"

FONT_SIZE_TOLERANCE = 1.5
SIZE_MAJOR_TOLERANCE = 10

TOP_REGION_RATIO = 0.30
LEFT_REGION_RATIO = 0.25

ADG_PALETTE = {
    "petrol_blue": "#02445B",
    "blanco": "#F6F6F6",
    "platino": "#CECECD",
    "obsidian_blue": "#01222E",
    "azul_digital": "#005C7F",
    "acero_glaciar": "#6A96A6",
}

TITLE_FONT_SIZE = 26
SUBTITLE_FONT_SIZE = 14
SECTION_NUMBER_FONT_SIZE = 100
SECTION_TITLE_FONT_SIZE = 36
SECTION_SUBTITLE_FONT_SIZE = 20
SECTION_NUMBER_MIN_DETECT_SIZE = 50
TITLE_COLOR = ADG_PALETTE["petrol_blue"]
SUBTITLE_COLOR = ADG_PALETTE["obsidian_blue"]

ALLOWED_SLIDE_COLORS = set(ADG_PALETTE.values()) | {"#FFFFFF", "#000000"}

APPROVED_FONTS = (
    "helveticaneue",
    "helvetica-neue",
    "helvetica neue",
    "helvetica",
    "elvetica",
    "elvética",
)

COLOR_TOLERANCE = 0.02

TEXT_RULES = {
    "header": {
        "color": TITLE_COLOR,
        "bold": True,
        "light": False,
        "font_size": TITLE_FONT_SIZE,
    },
    "subtitle": {
        "color": SUBTITLE_COLOR,
        "bold": False,
        "light": True,
        "font_size": SUBTITLE_FONT_SIZE,
    },
    "body": {
        "color": "#000000",
        "bold": False,
        "light": False,
        "font_size": None,
    },
}
