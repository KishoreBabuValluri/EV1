import React, { useEffect, useRef, useState } from 'react'

// ─── Custom hook to lazy-load Leaflet (avoids SSR issues) ───────────────────
function useLeaflet() {
  const [L, setL] = useState(null)
  useEffect(() => {
    import('leaflet').then(mod => {
      const leaflet = mod.default || mod
      // Fix default icon paths broken by bundlers
      delete leaflet.Icon.Default.prototype._getIconUrl
      leaflet.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
      })
      setL(leaflet)
    })
  }, [])
  return L
}

// ─── SVG marker factories ────────────────────────────────────────────────────

function makeStationIcon(L, available, total, color = '#00e5a0') {
  const pct = total > 0 ? (available / total) * 100 : 0
  const statusColor = pct > 50 ? '#00e5a0' : pct > 20 ? '#f59e0b' : '#ef4444'
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="42" height="54" viewBox="0 0 42 54">
      <defs>
        <filter id="shadow" x="-30%" y="-10%" width="160%" height="160%">
          <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="rgba(0,0,0,0.5)"/>
        </filter>
      </defs>
      <!-- Pin body -->
      <path d="M21 2C12.163 2 5 9.163 5 18c0 10.5 16 34 16 34s16-23.5 16-34C37 9.163 29.837 2 21 2z"
            fill="#0f1928" stroke="${statusColor}" stroke-width="2.5" filter="url(#shadow)"/>
      <!-- Lightning bolt -->
      <text x="21" y="23" text-anchor="middle" font-size="16" fill="${statusColor}">⚡</text>
      <!-- Availability ring background -->
      <circle cx="21" cy="18" r="10" fill="none" stroke="#1e2d45" stroke-width="2"/>
      <!-- Availability arc -->
      <circle cx="21" cy="18" r="10" fill="none" stroke="${statusColor}" stroke-width="2"
              stroke-dasharray="${(pct / 100) * 62.8} 62.8" stroke-dashoffset="15.7"
              stroke-linecap="round" opacity="0.4"/>
      <!-- Availability text -->
      <text x="21" y="34" text-anchor="middle" font-size="7" fill="#6b7fa3" font-family="monospace">${available}/${total}</text>
    </svg>`
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [42, 54],
    iconAnchor: [21, 54],
    popupAnchor: [0, -54],
  })
}

function makeLandIcon(L, score, locationType) {
  const typeEmoji = { highway: '🛣️', mall: '🏬', office: '🏢', residential: '🏘️', petrol_station: '⛽' }
  const emoji = typeEmoji[locationType] || '📍'
  const scoreColor = score > 85 ? '#00e5a0' : score > 70 ? '#00b4ff' : '#f59e0b'
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="44" height="56" viewBox="0 0 44 56">
      <defs>
        <filter id="shadow2" x="-30%" y="-10%" width="160%" height="160%">
          <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="rgba(0,0,0,0.5)"/>
        </filter>
      </defs>
      <!-- Diamond pin body -->
      <path d="M22 2C12.611 2 5 9.611 5 19c0 11 17 35 17 35s17-24 17-35C39 9.611 31.389 2 22 2z"
            fill="#0f1928" stroke="${scoreColor}" stroke-width="2.5" filter="url(#shadow2)"/>
      <!-- Location type emoji -->
      <text x="22" y="22" text-anchor="middle" font-size="13">${emoji}</text>
      <!-- Score badge -->
      <rect x="8" y="28" width="28" height="12" rx="6" fill="${scoreColor}" opacity="0.9"/>
      <text x="22" y="38" text-anchor="middle" font-size="8" fill="#0a0f1e" font-weight="bold" font-family="monospace">${score ? score.toFixed(0) : '?'}</text>
    </svg>`
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [44, 56],
    iconAnchor: [22, 56],
    popupAnchor: [0, -56],
  })
}

function makeSelectedIcon(L, color = '#00e5a0') {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="50" height="62" viewBox="0 0 50 62">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <path d="M25 2C14.507 2 6 10.507 6 21c0 12.5 19 39 19 39s19-26.5 19-39C44 10.507 35.493 2 25 2z"
            fill="#0f1928" stroke="${color}" stroke-width="3" filter="url(#glow)"/>
      <circle cx="25" cy="21" r="9" fill="${color}" opacity="0.25"/>
      <circle cx="25" cy="21" r="5" fill="${color}"/>
    </svg>`
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [50, 62],
    iconAnchor: [25, 62],
    popupAnchor: [0, -62],
  })
}

// ─── Popup HTML builders ─────────────────────────────────────────────────────

function stationPopupHtml(s) {
  const pct = s.total_points > 0 ? Math.round((s.available_points / s.total_points) * 100) : 0
  const statusColor = pct > 50 ? '#00e5a0' : pct > 20 ? '#f59e0b' : '#ef4444'
  const amenities = Array.isArray(s.amenities) ? s.amenities : (s.amenities || '').split(',').filter(Boolean)
  return `
    <div style="font-family:'DM Sans',sans-serif;background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:14px;min-width:220px;color:#e8f0fe;">
      <div style="font-weight:700;font-size:13px;margin-bottom:4px;color:#e8f0fe;">${s.name}</div>
      <div style="font-size:11px;color:#6b7fa3;margin-bottom:10px;">${s.address || s.city}</div>
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <div style="flex:1;background:#161d2e;border-radius:8px;padding:8px;text-align:center;">
          <div style="font-size:18px;font-weight:700;color:${statusColor};">${s.available_points}</div>
          <div style="font-size:9px;color:#6b7fa3;text-transform:uppercase;">Free of ${s.total_points}</div>
        </div>
        <div style="flex:1;background:#161d2e;border-radius:8px;padding:8px;text-align:center;">
          <div style="font-size:18px;font-weight:700;color:#00b4ff;">₹${s.price_per_kwh}</div>
          <div style="font-size:9px;color:#6b7fa3;text-transform:uppercase;">per kWh</div>
        </div>
      </div>
      <div style="background:#161d2e;border-radius:6px;overflow:hidden;height:4px;margin-bottom:8px;">
        <div style="height:100%;width:${pct}%;background:${statusColor};transition:width 0.5s;"></div>
      </div>
      ${amenities.length > 0 ? `<div style="font-size:10px;color:#6b7fa3;margin-bottom:8px;">${amenities.map(a => `<span style="background:#1e2d45;border-radius:4px;padding:2px 6px;margin-right:3px;">${a}</span>`).join('')}</div>` : ''}
      <div style="font-size:10px;color:${s.uptime_percent > 95 ? '#00e5a0' : '#f59e0b'};">⬤ ${s.uptime_percent || 99}% uptime</div>
    </div>`
}

function landPopupHtml(l) {
  const typeLabel = { highway: 'Highway', mall: 'Mall/Retail', office: 'Office/IT', residential: 'Residential', petrol_station: 'Petrol Station' }
  const scoreColor = l.ai_score > 85 ? '#00e5a0' : l.ai_score > 70 ? '#00b4ff' : '#f59e0b'
  return `
    <div style="font-family:'DM Sans',sans-serif;background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:14px;min-width:220px;color:#e8f0fe;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <div style="font-weight:700;font-size:13px;max-width:160px;">${l.title}</div>
        ${l.ai_score ? `<div style="background:${scoreColor}20;border:1px solid ${scoreColor}50;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;color:${scoreColor};">${l.ai_score.toFixed(1)}</div>` : ''}
      </div>
      <div style="font-size:11px;color:#6b7fa3;margin-bottom:10px;">${l.address || l.city}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">
        <div style="background:#161d2e;border-radius:8px;padding:8px;">
          <div style="font-size:12px;font-weight:600;">₹${l.monthly_lease?.toLocaleString()}</div>
          <div style="font-size:9px;color:#6b7fa3;">per month</div>
        </div>
        <div style="background:#161d2e;border-radius:8px;padding:8px;">
          <div style="font-size:12px;font-weight:600;">${l.area_sqft?.toLocaleString()} sqft</div>
          <div style="font-size:9px;color:#6b7fa3;">${typeLabel[l.location_type] || l.location_type}</div>
        </div>
      </div>
      ${l.daily_traffic ? `<div style="font-size:10px;color:#6b7fa3;">🚗 ${l.daily_traffic.toLocaleString()} vehicles/day</div>` : ''}
      ${l.power_availability ? `<div style="font-size:10px;color:#6b7fa3;margin-top:3px;">⚡ ${l.power_availability}</div>` : ''}
    </div>`
}

// ─── MAIN EVMap COMPONENT ────────────────────────────────────────────────────

/**
 * EVMap — universal reusable Leaflet map
 *
 * Props:
 *   stations  — array of ChargingStation objects (optional)
 *   lands     — array of LandListing objects (optional)
 *   center    — [lat, lon] default center
 *   zoom      — default zoom
 *   height    — CSS height string (default '100%')
 *   onStationClick(station) — callback when a station marker is clicked
 *   onLandClick(listing)    — callback when a land marker is clicked
 *   selectedId — id of currently selected item (gets enlarged marker)
 *   selectedType — 'station' | 'land'
 *   showLegend — bool (default true)
 *   mapId      — unique string (required when using multiple maps on page)
 */
export default function EVMap({
  stations = [],
  lands = [],
  center = [17.4399, 78.4983],
  zoom = 11,
  height = '100%',
  onStationClick,
  onLandClick,
  selectedId,
  selectedType,
  showLegend = true,
  mapId = 'ev-map',
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const L = useLeaflet()

  // Init map once L is loaded
  useEffect(() => {
    if (!L || !containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      center,
      zoom,
      zoomControl: false,
      attributionControl: false,
    })

    // Dark tile layer (CartoDB dark matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap, © CartoDB',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map)

    // Zoom controls bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    // Attribution bottom left, styled
    L.control.attribution({ position: 'bottomleft', prefix: '' })
      .addAttribution('<span style="color:#2d4060;font-size:9px;">© OSM · CartoDB</span>')
      .addTo(map)

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [L])

  // Update markers whenever data or selection changes
  useEffect(() => {
    const map = mapRef.current
    if (!L || !map) return

    // Clear existing markers
    markersRef.current.forEach(m => map.removeLayer(m))
    markersRef.current = []

    // Station markers
    stations.forEach(s => {
      if (!s.latitude || !s.longitude) return
      const isSelected = selectedType === 'station' && selectedId === s.id
      const icon = isSelected
        ? makeSelectedIcon(L, '#00e5a0')
        : makeStationIcon(L, s.available_points, s.total_points)

      const marker = L.marker([s.latitude, s.longitude], { icon })
        .bindPopup(stationPopupHtml(s), {
          className: 'ev-leaflet-popup',
          maxWidth: 260,
          closeButton: false,
        })
        .addTo(map)

      marker.on('click', () => { onStationClick?.(s) })
      if (isSelected) marker.openPopup()
      markersRef.current.push(marker)
    })

    // Land markers
    lands.forEach(l => {
      if (!l.latitude || !l.longitude) return
      const isSelected = selectedType === 'land' && selectedId === l.id
      const icon = isSelected
        ? makeSelectedIcon(L, '#00e5a0')
        : makeLandIcon(L, l.ai_score, l.location_type)

      const marker = L.marker([l.latitude, l.longitude], { icon })
        .bindPopup(landPopupHtml(l), {
          className: 'ev-leaflet-popup',
          maxWidth: 260,
          closeButton: false,
        })
        .addTo(map)

      marker.on('click', () => { onLandClick?.(l) })
      if (isSelected) marker.openPopup()
      markersRef.current.push(marker)
    })

    // Fit bounds to all markers if we have some
    const allPoints = [
      ...stations.filter(s => s.latitude && s.longitude).map(s => [s.latitude, s.longitude]),
      ...lands.filter(l => l.latitude && l.longitude).map(l => [l.latitude, l.longitude]),
    ]
    if (allPoints.length > 1 && !selectedId) {
      map.fitBounds(allPoints, { padding: [40, 40], maxZoom: 14 })
    } else if (allPoints.length === 1) {
      map.setView(allPoints[0], 13)
    }
  }, [L, stations, lands, selectedId, selectedType, onStationClick, onLandClick])

  return (
    <div style={{ position: 'relative', height, width: '100%' }}>
      {/* Map container */}
      <div ref={containerRef} style={{ height: '100%', width: '100%', borderRadius: '12px', overflow: 'hidden' }} />

      {/* Legend */}
      {showLegend && (
        <div style={{
          position: 'absolute', bottom: 36, left: 12, zIndex: 1000,
          background: 'rgba(11,15,30,0.92)', backdropFilter: 'blur(8px)',
          border: '1px solid #1e2d45', borderRadius: 10, padding: '8px 12px',
          fontFamily: "'DM Sans',sans-serif", fontSize: 10, color: '#6b7fa3',
        }}>
          {stations.length > 0 && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span style={{ color: '#00e5a0', fontSize: 12 }}>⚡</span> Charging Station
              </div>
              <div style={{ display: 'flex', gap: 10, marginBottom: lands.length > 0 ? 6 : 0 }}>
                <span style={{ color: '#00e5a0' }}>● Available</span>
                <span style={{ color: '#f59e0b' }}>● Partial</span>
                <span style={{ color: '#ef4444' }}>● Full</span>
              </div>
            </>
          )}
          {lands.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12 }}>📍</span> Land Listing (score shown)
            </div>
          )}
        </div>
      )}

      {/* Leaflet popup dark style */}
      <style>{`
        .ev-leaflet-popup .leaflet-popup-content-wrapper,
        .ev-leaflet-popup .leaflet-popup-tip {
          background: transparent !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .ev-leaflet-popup .leaflet-popup-content {
          margin: 0 !important;
        }
        .leaflet-container {
          background: #0a0f1e !important;
          font-family: 'DM Sans', sans-serif !important;
        }
        .leaflet-control-zoom a {
          background: #111827 !important;
          color: #6b7fa3 !important;
          border-color: #1e2d45 !important;
        }
        .leaflet-control-zoom a:hover {
          background: #161d2e !important;
          color: #00e5a0 !important;
        }
      `}</style>
    </div>
  )
}
