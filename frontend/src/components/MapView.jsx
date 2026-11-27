import { useEffect, useMemo, useRef } from "react";
import Button from "@mui/material/Button";
import L from "leaflet";
import {
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  useMap,
} from "react-leaflet";
import { designTokens } from "../theme.js";
import {
  hasCoordinates,
  overviewPoints,
  routePoints,
} from "../utils/itinerary.js";
import Icon from "./Icon.jsx";

const numberIcon = (number, selected) =>
  L.divIcon({
    className: `num-marker ${selected ? "selected" : ""}`,
    html: `<span>${number}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });

function MapViewport({ plan, selectedPoi, center, selection, routeViewKey }) {
  const map = useMap();
  const bounds = useMemo(() => overviewPoints(plan), [plan]);
  const viewport = useRef(null);
  viewport.current = { bounds, selectedPoi, plan, center };
  const fit = () => {
    if (bounds.length)
      map.fitBounds(bounds, { padding: [55, 55], maxZoom: 15 });
    else map.setView(center, 14);
  };
  useEffect(() => {
    fit();
  }, [plan, center, routeViewKey, map]);
  useEffect(() => {
    const stop = plan?.stops?.find((item) => item.poi_id === selectedPoi);
    if (hasCoordinates(stop)) {
      map.setView([stop.lat, stop.lng], 15, { animate: false });
      if (window.matchMedia("(max-width:800px)").matches)
        map.panBy([0, map.getSize().y * 0.2], { animate: false });
    }
  }, [selectedPoi, selection, plan, map]);
  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    let wasHidden = true;
    const observer = new ResizeObserver(([entry]) => {
      const visible =
        entry.contentRect.width > 0 && entry.contentRect.height > 0;
      map.invalidateSize({ pan: false });
      if (visible && wasHidden) {
        const current = viewport.current;
        const stop = current.plan?.stops?.find(
          (item) => item.poi_id === current.selectedPoi,
        );
        if (hasCoordinates(stop)) {
          map.setView([stop.lat, stop.lng], 15, { animate: false });
          if (window.matchMedia("(max-width:800px)").matches)
            map.panBy([0, map.getSize().y * 0.2], { animate: false });
        } else if (current.bounds.length)
          map.fitBounds(current.bounds, { padding: [55, 55], maxZoom: 15 });
        else map.setView(current.center, 14);
      }
      wasHidden = !visible;
    });
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

function StopMarker({ stop, index, selected, onSelect }) {
  return (
    <Marker
      position={[stop.lat, stop.lng]}
      icon={numberIcon(index + 1, selected)}
      title={`${index + 1}. ${stop.name?.vi || stop.poi_id}`}
      alt={`${index + 1}. ${stop.name?.vi || stop.poi_id}`}
      eventHandlers={{ click: () => onSelect(stop.poi_id) }}
    />
  );
}

export default function MapView({
  center,
  plan,
  onSelect,
  selectedPoi,
  selection,
  routeViewKey,
  onShowRoute,
}) {
  const stops = plan?.stops || [];
  const geometry = routePoints(plan);
  const fallback = stops
    .filter(hasCoordinates)
    .map((stop) => [stop.lat, stop.lng]);
  const positions = geometry.length > 1 ? geometry : fallback;
  return (
    <>
      <MapContainer center={center} zoom={14} className="map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {stops.map((stop, index) =>
          hasCoordinates(stop) ? (
            <StopMarker
              key={stop.poi_id}
              stop={stop}
              index={index}
              selected={selectedPoi === stop.poi_id}
              onSelect={onSelect}
            />
          ) : null,
        )}
        {positions.length > 1 && (
          <Polyline
            positions={positions}
            weight={4}
            color={designTokens.primary}
            dashArray={geometry.length > 1 ? undefined : "8 7"}
          />
        )}
        <MapViewport
          plan={plan}
          selectedPoi={selectedPoi}
          center={center}
          selection={selection}
          routeViewKey={routeViewKey}
        />
      </MapContainer>
      <div className="map-route-controls">
        <Button
          variant="contained"
          onClick={onShowRoute}
          disabled={!stops.some(hasCoordinates)}
          startIcon={<Icon />}
        >
          Xem toàn tuyến
        </Button>
        {plan && geometry.length < 2 && (
          <span>Đường nối minh họa, chưa có chỉ dẫn đường.</span>
        )}
      </div>
    </>
  );
}
