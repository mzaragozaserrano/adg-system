import { useCallback, useEffect, useRef, useState } from "react";
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

const MAX_RETRIES = 3;
const RETRY_DELAYS_MS = [2000, 5000, 10000];

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
  const concurrency = 3;
  let cursor = 0;

  const worker = async () => {
    while (cursor < pending.length) {
      const slideNumber = pending[cursor];
      cursor += 1;
      const key = thumbnailCacheKey(presentationId, slideNumber);
      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        if (attempt > 0) {
          await new Promise((res) => setTimeout(res, RETRY_DELAYS_MS[attempt - 1] ?? 10000));
        }
        try {
          const url = await fetchThumbnail(presentationId, slideNumber);
          thumbnailCache.set(key, url);
          break;
        } catch {
          if (attempt === MAX_RETRIES) break;
        }
      }
      remaining -= 1;
      onLoaded?.();
      if (remaining <= 0) return;
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
  const [retryCount, setRetryCount] = useState(0);
  const activeRef = useRef(true);

  const load = useCallback(() => {
    const cached = thumbnailCache.get(cacheKey);
    if (cached) {
      setSrc(cached);
      setLoading(false);
      return;
    }
    activeRef.current = true;
    setLoading(true);
    fetchThumbnail(presentationId, slideNumber)
      .then((url) => {
        thumbnailCache.set(cacheKey, url);
        if (activeRef.current) {
          setSrc(url);
          setLoading(false);
        }
      })
      .catch(() => {
        if (activeRef.current) {
          setLoading(false);
        }
      });
  }, [cacheKey, presentationId, slideNumber]);

  useEffect(() => {
    activeRef.current = true;
    load();
    return () => { activeRef.current = false; };
  }, [load, cacheVersion, retryCount]);

  const className = variant === "issue" ? "slide-thumb slide-thumb-issue" : "slide-thumb slide-thumb-summary";
  const hasSrc = Boolean(src);

  if (loading) {
    return (
      <div className={`${className} slide-thumb-placeholder`} aria-label={`Cargando diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
      </div>
    );
  }

  if (!hasSrc) {
    return (
      <div className={`${className} slide-thumb-placeholder slide-thumb-missing`} aria-label={`Diapositiva ${slideNumber}`}>
        <span>{slideNumber}</span>
        {retryCount < MAX_RETRIES && (
          <button
            className="slide-thumb-retry"
            title="Reintentar carga"
            onClick={() => setRetryCount((c) => c + 1)}
          >
            ↺
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="slide-thumb-wrap">
      <div className="slide-thumb-hover">
        <img className={className} src={src!} alt={`Diapositiva ${slideNumber}`} />
        <div className="slide-thumb-zoom" aria-hidden="true">
          <img src={src!} alt="" />
        </div>
      </div>
      {showLabel && <span className="slide-thumb-label">Diap. {slideNumber}</span>}
    </div>
  );
}
