import time
from typing import Any

CACHE_TTL_SECONDS = 120
_presentation_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def get_cached_presentation(
    slides_service,
    presentation_id: str,
    *,
    ttl: int = CACHE_TTL_SECONDS,
) -> dict[str, Any]:
    now = time.time()
    cached = _presentation_cache.get(presentation_id)
    if cached and now - cached[0] < ttl:
        return cached[1]
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    _presentation_cache[presentation_id] = (now, presentation)
    return presentation


def invalidate_presentation_cache(presentation_id: str) -> None:
    _presentation_cache.pop(presentation_id, None)
