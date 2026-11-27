export const formatMoney = (value) =>
  Number.isFinite(value)
    ? `${value.toLocaleString("vi-VN")}đ`
    : "Chưa có chi phí";
export const hasCoordinates = (stop) =>
  Number.isFinite(stop?.lat) &&
  Number.isFinite(stop?.lng) &&
  Math.abs(stop.lat) <= 90 &&
  Math.abs(stop.lng) <= 180;
export const routePoints = (plan) =>
  (plan?.polyline || []).filter(
    (point) =>
      Array.isArray(point) && hasCoordinates({ lat: point[0], lng: point[1] }),
  );
export function overviewPoints(plan) {
  return [
    ...routePoints(plan),
    ...(plan?.stops || [])
      .filter(hasCoordinates)
      .map((stop) => [stop.lat, stop.lng]),
  ];
}
