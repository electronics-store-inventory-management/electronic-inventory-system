import { useCallback, useEffect, useRef, useState } from "react";

export function useLoad(loader) {
  const [state, setState] = useState({ data: [], loading: true, error: "" });
  const requestNumber = useRef(0);

  const load = useCallback(async (request) => {
    try {
      const data = await loader();
      if (requestNumber.current === request) setState({ data, loading: false, error: "" });
    } catch (error) {
      if (requestNumber.current === request) {
        setState((current) => ({ ...current, loading: false, error: error.message || "Could not load data" }));
      }
    }
  }, [loader]);

  const refresh = useCallback(() => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    void load(++requestNumber.current);
  }, [load]);

  useEffect(() => {
    void load(++requestNumber.current);
    return () => { requestNumber.current += 1; };
  }, [load]);

  return { ...state, refresh };
}
