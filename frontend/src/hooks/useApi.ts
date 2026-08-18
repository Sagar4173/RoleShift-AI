import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../services/api";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => void;
}

/**
 * Data-fetching hook.
 *
 * `deps` must contain only stable primitive values (e.g. ids, strings, numbers).
 * The fetcher itself is intentionally excluded from the effect dependencies to
 * prevent infinite render/request loops; a change in `deps` (or a manual
 * `refetch`) triggers a fresh request.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: readonly unknown[] = [],
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const depsKey = deps.join("|");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err
              : new ApiError(
                  0,
                  "unknown_error",
                  err instanceof Error ? err.message : "Unknown error",
                ),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, depsKey]);

  const refetch = useCallback(() => setTick((value) => value + 1), []);

  return { data, loading, error, refetch };
}
