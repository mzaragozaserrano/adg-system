import { useCallback, useRef, useState } from "react";
import type { FixState } from "../../types";

interface FixJob {
  issueIds: string[];
  scopeKey: string;
  colorOverride?: string;
  colorByIssueId?: Record<string, string>;
}

export function useFixQueue(
  onExecute: (
    issueIds: string[],
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => Promise<void>,
  onError?: (message: string) => void
) {
  const [fixStates, setFixStates] = useState<Record<string, FixState>>({});
  const queueRef = useRef<FixJob[]>([]);
  const processingRef = useRef(false);
  const fixStatesRef = useRef(fixStates);
  const onExecuteRef = useRef(onExecute);
  const onErrorRef = useRef(onError);

  fixStatesRef.current = fixStates;
  onExecuteRef.current = onExecute;
  onErrorRef.current = onError;

  const drainQueue = useCallback(async () => {
    if (processingRef.current) return;

    const job = queueRef.current.shift();
    if (!job) return;

    processingRef.current = true;
    try {
      await onExecuteRef.current(job.issueIds, {
        colorOverride: job.colorOverride,
        colorByIssueId: job.colorByIssueId,
      });
      setFixStates((prev) => {
        const next = { ...prev };
        for (const id of job.issueIds) delete next[id];
        if (job.scopeKey === "batch") delete next.batch;
        return next;
      });
    } catch (err) {
      onErrorRef.current?.(err instanceof Error ? err.message : "Error al corregir");
      setFixStates((prev) => {
        const next = { ...prev };
        for (const id of job.issueIds) {
          if (next[id] === "fixing") next[id] = "error";
        }
        if (job.scopeKey === "batch" && next.batch === "fixing") next.batch = "error";
        return next;
      });
    } finally {
      processingRef.current = false;
      void drainQueue();
    }
  }, []);

  const enqueue = useCallback((
    issueIds: string[],
    scopeKey: string,
    options?: { colorOverride?: string; colorByIssueId?: Record<string, string> }
  ) => {
    if (issueIds.length === 0) return;

    const states = fixStatesRef.current;
    if (issueIds.some((id) => states[id] === "fixing")) return;
    if (scopeKey === "batch" && states.batch === "fixing") return;

    setFixStates((prev) => {
      const next = { ...prev };
      for (const id of issueIds) next[id] = "fixing";
      if (scopeKey === "batch") next.batch = "fixing";
      return next;
    });

    queueRef.current.push({ issueIds, scopeKey, colorOverride: options?.colorOverride, colorByIssueId: options?.colorByIssueId });
    void drainQueue();
  }, [drainQueue]);

  const reset = useCallback(() => {
    queueRef.current = [];
    processingRef.current = false;
    setFixStates({});
  }, []);

  const clearBatchScope = useCallback(() => {
    setFixStates((prev) => {
      if (prev.batch !== "fixed" && prev.batch !== "error") return prev;
      const next = { ...prev };
      delete next.batch;
      return next;
    });
  }, []);

  return { enqueue, reset, clearBatchScope, fixStates };
}
