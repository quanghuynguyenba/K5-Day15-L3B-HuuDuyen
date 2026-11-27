import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

export default function usePoiCatalogue() {
  const [state, setState] = useState({ pois: [], loading: true, error: null });
  const [version, setVersion] = useState(0);
  const retry = useCallback(() => setVersion((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: null }));
    api
      .pois()
      .then((pois) => {
        if (!Array.isArray(pois) || pois.some((poi) => !poi?.id || !poi.name))
          throw new Error("Danh sách địa điểm từ API chưa hợp lệ.");
        if (active) setState({ pois, loading: false, error: null });
      })
      .catch((error) => {
        if (active)
          setState((current) => ({
            ...current,
            loading: false,
            error: error.message,
          }));
      });
    return () => {
      active = false;
    };
  }, [version]);
  return { ...state, retry };
}
