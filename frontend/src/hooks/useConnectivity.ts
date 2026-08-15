import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../services/api";

type Status = "checking" | "connected" | "offline";

/**
 * Lightweight backend connectivity probe. Checks once on mount and re-checks
 * on an interval, using a real API call (never a fabricated status).
 */
export function useConnectivity(intervalMs = 30000): Status {
  const [status, setStatus] = useState<Status>("checking");
  const mounted = useRef(true);

  const check = useCallback(() => {
    api
      .listSkills(0, 1)
      .then(() => {
        if (mounted.current) setStatus("connected");
      })
      .catch(() => {
        if (mounted.current) setStatus("offline");
      });
  }, []);

  useEffect(() => {
    mounted.current = true;
    check();
    const timer = setInterval(check, intervalMs);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [check, intervalMs]);

  return status;
}
