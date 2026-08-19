import { useEffect, useState } from "react";
import { fetchThumbnail } from "../api";

const thumbnailCache = new Map<string, string>();

export function thumbnailCacheKey(presentationId: string, slideNumber: number): string {
  return `${presentationId}:${slideNumber}`;
}

export function clearThumbnailCache(): void {
  for (const url of thumbnailCache.values()) {
    URL.revokeObjectURL(url);
  }
  thumbnailCache.clear();
}

export function preloadSlideThumbnails(
  presentationId: string,
  slideNumbers: number[],
  onLoaded?: () => void
) {
  const pending = slideNumbers.filter(
    (n) => !thumbnailCache.has(thumbnailCacheKey(presentationId, n))
  );
  if (pending.length === 0) {
    onLoaded?.();
    return;
  }

  let remaining = pending.length;
  const concurrency = 6;
  let cursor = 0;

  const worker = async () => {
    while (cursor < pending.length) {
      const slideNumber = pending[cursor];
      cursor += 1;
      const key = thumbnailCacheKey(presentationId, slideNumber);
      try {
        const url = await fetchThumbnail(presentationId, slideNumber);
        thumbnailCache.set(key, url);
      } catch {
        // ignored
      } finally {
        remaining -= 1;
        onLoaded?.();
        if (remaining <= 0) return;
      }
    }
  };

  void Promise.all(Array.from({ length: Math.min(concurrency, pending.length) }, () => worker()));
}

export default function SlideThumbnail({
  presentationId,
  slideNumber,
  variant = "summary",
  showLabel = variant === "issue",
  cacheVersion = 0,
}: {
  presentationId: string;
  slideNumber: number;
  variant?: "summary" | "issue";
  showLabel?: boolean;
  cacheVersion?: number;
}) {
  const cacheKey = thumbnailCacheKey(presentationId, slideNumber);
  const [src, setSrc] = useState<string | null>(() => thumbnailCache.get(cacheKey) || null);
  const [loading, setLoading] = useState(!thumbnailCache.has(cacheKey));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const cached = thumbnailCache.get(cacheKey);
    if (cached) {
      setSrc(cached);
      setLoading(false);
      setFailed(false);
      return;
    }

    let active = true;
    setLoading(true);
    setFailed(false);
    fetchThumbnail(presentationId, slideNumber)
      .then((url) => {
        thumbnailCache.set(cacheKey, url);
        if (active) {
          setSrc(url);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true);
          setLoading(false);
        }
      });

    return () => { active = false; };
  }, [cacheKey, presentationId, slideNumber, cacheVersion]);

  const className = variant === "issue" ? "slide-thumb slide-thumb-issue" : "slide-thumb slide-thumb-summary";

  if (loading) {
    return (
      <div className={`${className} slide-thumb-placeholder`} aria-label={`Cargando diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
      </div>
    );
  }

  if (failed || !src) {
    return (
      <div className={`${className} slide-thumb-placeholder slide-thumb-missing`} aria-label={`Diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
      </div>
    );
  }

  return (
    <div className="slide-thumb-wrap">
      <div className="slide-thumb-hover">
        <img className={className} src={src} alt={`Diapositiva ${slideNumber}`} />
        <div className="slide-thumb-zoom" aria-hidden="true">
          <img src={src} alt="" />
        </div>
      </div>
      {showLabel && <span className="slide-thumb-label">Diap. {slideNumber}</span>}
    </div>
  );
}
