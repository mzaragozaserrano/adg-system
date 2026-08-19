from config.brand_guidelines import ADG_PALETTE, ALLOWED_SLIDE_COLORS, COLOR_TOLERANCE

PALETTE_COLOR_NAMES = {
    ADG_PALETTE["petrol_blue"].upper(): "Petrol Blue",
    ADG_PALETTE["blanco"].upper(): "Blanco",
    ADG_PALETTE["platino"].upper(): "Platino",
    ADG_PALETTE["obsidian_blue"].upper(): "Obsidian Blue",
    ADG_PALETTE["azul_digital"].upper(): "Azul Digital",
    ADG_PALETTE["acero_glaciar"].upper(): "Acero Glaciar",
    "#FFFFFF": "Blanco",
    "#000000": "Negro",
}


def rgb_to_hex(red: float, green: float, blue: float) -> str:
    r = max(0, min(255, round(red * 255)))
    g = max(0, min(255, round(green * 255)))
    b = max(0, min(255, round(blue * 255)))
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_tuple_to_hex(rgb: tuple) -> str | None:
    if not rgb or len(rgb) < 3:
        return None
    return rgb_to_hex(rgb[0], rgb[1], rgb[2])


def int_to_hex(color_int: int) -> str:
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb_normalized(hex_color: str) -> dict:
    h = hex_color.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue": int(h[4:6], 16) / 255,
    }


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def colors_match(hex_a: str, hex_b: str, tolerance: float = COLOR_TOLERANCE) -> bool:
    if hex_a.upper() == hex_b.upper():
        return True
    ra, ga, ba = hex_to_rgb(hex_a)
    rb, gb, bb = hex_to_rgb(hex_b)
    return (
        abs(ra - rb) <= tolerance
        and abs(ga - gb) <= tolerance
        and abs(ba - bb) <= tolerance
    )


def is_allowed_palette_color(hex_color: str) -> bool:
    return any(colors_match(hex_color, allowed) for allowed in ALLOWED_SLIDE_COLORS)


def _rgb_ints(hex_color: str) -> tuple[int, int, int]:
    normalized = hex_color.lstrip("#").upper()
    return (
        int(normalized[0:2], 16),
        int(normalized[2:4], 16),
        int(normalized[4:6], 16),
    )


def _color_distance_squared(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> float:
    return float(sum((a - b) ** 2 for a, b in zip(left, right)))


def nearest_palette_colors(hex_color: str, limit: int = 3) -> list[str]:
    if not hex_color or hex_color.startswith("theme:"):
        return ["#000000"]

    normalized = normalize_hex(hex_color)
    if len(normalized) != 7 or not normalized.startswith("#"):
        return ["#000000"]

    rgb = _rgb_ints(normalized)
    candidates = sorted(
        {color.upper() for color in ALLOWED_SLIDE_COLORS},
        key=lambda candidate: _color_distance_squared(rgb, _rgb_ints(candidate)),
    )
    return candidates[:limit]


def nearest_palette_color(hex_color: str) -> str:
    return nearest_palette_colors(hex_color, 1)[0]


def describe_palette_color(hex_color: str) -> str:
    normalized = hex_color.upper()
    name = PALETTE_COLOR_NAMES.get(normalized, "Paleta ADG")
    return f"{name} ({normalized})"


def suggest_palette_color(hex_color: str) -> tuple[str, str]:
    suggested = nearest_palette_color(hex_color)
    return suggested, describe_palette_color(suggested)


def normalize_hex(hex_color: str) -> str:
    normalized = hex_color.strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    return normalized


def palette_violation_metadata(hex_color: str, limit: int = 3) -> dict:
    normalized = normalize_hex(hex_color)
    suggestions = nearest_palette_colors(normalized, limit)
    primary = suggestions[0]
    return {
        "expected": describe_palette_color(primary),
        "actual": normalized,
        "color_actual": normalized,
        "color_suggested": primary,
        "color_suggestions": [
            {"color": suggested, "label": describe_palette_color(suggested)}
            for suggested in suggestions
        ],
    }


def extract_rgb_from_slides_color(color_obj: dict | None) -> str | None:
    if not color_obj:
        return None
    opaque = color_obj.get("opaqueColor", {})
    rgb = opaque.get("rgbColor")
    if rgb:
        return rgb_to_hex(rgb.get("red", 0), rgb.get("green", 0), rgb.get("blue", 0))
    theme = opaque.get("themeColor")
    if theme:
        return f"theme:{theme}"
    return None
