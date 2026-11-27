import { useEffect } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'

const numberIcon = (n) =>
  L.divIcon({ className: 'num-marker', html: `<span>${n}</span>`, iconSize: [28, 28], iconAnchor: [14, 14] })

const vnd = (n) => n.toLocaleString('vi-VN')

function FitBounds({ plan }) {
  const map = useMap()
  useEffect(() => {
    if (plan?.polyline?.length > 1) map.fitBounds(plan.polyline, { padding: [30, 30] })
  }, [plan, map])
  return null
}

export default function MapView({ center, plan, onSelect }) {
  return (
    <MapContainer center={center} zoom={14} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {plan?.stops.map((s, i) => (
        <Marker
          key={s.poi_id}
          position={[s.lat, s.lng]}
          icon={numberIcon(i + 1)}
          eventHandlers={{ click: () => onSelect(s.poi_id) }}
        >
          <Popup>
            <b>{s.name?.vi}</b><br />
            {s.arrive}–{s.depart} · {vnd(s.cost)} VND
          </Popup>
        </Marker>
      ))}
      {plan?.polyline?.length > 1 && <Polyline positions={plan.polyline} weight={4} />}
      <FitBounds plan={plan} />
    </MapContainer>
  )
}
