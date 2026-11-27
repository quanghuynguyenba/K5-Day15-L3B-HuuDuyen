import { useEffect, useRef } from "react";
import { designTokens } from "../theme.js";
import L from "leaflet";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

const numberIcon = (n, selected) =>
  L.divIcon({
    className: `num-marker ${selected ? "selected" : ""}`,
    html: `<span>${n}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });

const vnd = (n) => n.toLocaleString("vi-VN");

function FitBounds({ plan, selectedPoi, center }) {
  const map = useMap();
  const container = map.getContainer();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(container);
    return () => observer.disconnect();
  }, [map, container]);
  useEffect(() => {
    if (plan?.polyline?.length > 1)
      map.fitBounds(plan.polyline, { padding: [70, 70] });
    else map.setView(center, 14);
  }, [plan, map, center]);
  useEffect(() => {
    const stop = plan?.stops.find((s) => s.poi_id === selectedPoi);
    if (stop) map.flyTo([stop.lat, stop.lng], 14, { duration: 0.5 });
  }, [selectedPoi, plan, map]);
  return null;
}

function StopMarker({ stop: s, index, selected, onSelect }) {
  const marker = useRef(null);
  useEffect(() => {
    if (selected) marker.current?.openPopup();
  }, [selected]);
  return (
    <Marker
      ref={marker}
      position={[s.lat, s.lng]}
      icon={numberIcon(index + 1, selected)}
      eventHandlers={{ click: () => onSelect(s.poi_id) }}
    >
      <Popup>
        <b>{s.name?.vi}</b>
        <br />
        {s.arrive}–{s.depart} · {vnd(s.cost)} VND
      </Popup>
    </Marker>
  );
}

export default function MapView({ center, plan, onSelect, selectedPoi }) {
  return (
    <MapContainer center={center} zoom={14} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {plan?.stops
        .filter((s) => Number.isFinite(s.lat) && Number.isFinite(s.lng))
        .map((s, i) => (
          <StopMarker
            key={s.poi_id}
            stop={s}
            index={i}
            selected={selectedPoi === s.poi_id}
            onSelect={onSelect}
          />
        ))}
      {plan?.polyline?.length > 1 && (
        <Polyline
          positions={plan.polyline}
          weight={4}
          color={designTokens.primary}
          dashArray="8 7"
        />
      )}
      <FitBounds plan={plan} selectedPoi={selectedPoi} center={center} />
    </MapContainer>
  );
}
