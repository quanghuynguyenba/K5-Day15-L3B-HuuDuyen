import { useCallback, useEffect, useRef, useState } from "react";

// Vị trí hiện tại của người dùng (GPS / Wi-Fi của trình duyệt).
// status: "idle" | "pending" | "ok" | "denied" | "unavailable" | "unsupported"
// location: { lat, lng, accuracy } — gửi kèm mỗi tin chat để backend lấy làm điểm xuất phát.
// Trình duyệt chỉ cho geolocation trên https hoặc localhost.
export default function useGeolocation({ auto = true } = {}) {
  const [state, setState] = useState({ status: "idle", location: null, error: null });
  const watchId = useRef(null);

  const stop = useCallback(() => {
    if (watchId.current !== null) navigator.geolocation?.clearWatch(watchId.current);
    watchId.current = null;
  }, []);

  const start = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setState({ status: "unsupported", location: null, error: "Trình duyệt không hỗ trợ định vị." });
      return;
    }
    stop();
    setState((s) => ({ ...s, status: s.location ? "ok" : "pending", error: null }));
    watchId.current = navigator.geolocation.watchPosition(
      (pos) =>
        setState({
          status: "ok",
          error: null,
          location: {
            lat: +pos.coords.latitude.toFixed(6),
            lng: +pos.coords.longitude.toFixed(6),
            accuracy: Math.round(pos.coords.accuracy),
          },
        }),
      (err) =>
        setState((s) => ({
          ...s,
          status: err.code === err.PERMISSION_DENIED ? "denied" : s.location ? "ok" : "unavailable",
          error:
            err.code === err.PERMISSION_DENIED
              ? "Bạn đã chặn quyền vị trí — lịch trình sẽ xuất phát từ Hồ Gươm."
              : "Chưa lấy được vị trí hiện tại.",
        })),
      { enableHighAccuracy: true, maximumAge: 60000, timeout: 15000 },
    );
  }, [stop]);

  useEffect(() => {
    if (auto) start();
    return stop;
  }, [auto, start, stop]);

  return { ...state, retry: start };
}
