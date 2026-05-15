/**
 * useSSE — subscribes to /api/sse/availability and patches station state live.
 *
 * Usage:
 *   const { liveStations, connected } = useSSE(stations)
 *
 * - `liveStations` is always in sync with the latest SSE availability events
 * - `connected` reflects the EventSource readyState
 * - Automatically reconnects after 3s on error
 * - Passes JWT via ?token= query param (EventSource can't set headers)
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const SSE_URL = '/api/sse/availability'
const RECONNECT_DELAY_MS = 3000

export function useSSE(initialStations = []) {
  const [liveStations, setLiveStations] = useState(initialStations)
  const [connected, setConnected] = useState(false)
  const esRef = useRef(null)
  const reconnectTimer = useRef(null)

  // Keep a ref of latest stations for patching (avoids stale closures)
  const stationsRef = useRef(liveStations)
  useEffect(() => {
    stationsRef.current = liveStations
  }, [liveStations])

  // Sync when parent passes new initialStations (e.g. after API fetch)
  useEffect(() => {
    setLiveStations(initialStations)
  }, [JSON.stringify(initialStations.map(s => s.id))]) // eslint-disable-line

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    const token = localStorage.getItem('cn_token')
    const url = token ? `${SSE_URL}?token=${encodeURIComponent(token)}` : SSE_URL
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('connected', () => setConnected(true))

    es.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data)
        if (evt.type === 'availability' || evt.type === 'point_status') {
          setLiveStations(prev =>
            prev.map(s =>
              s.id === evt.station_id
                ? { ...s, available_points: evt.available_points, total_points: evt.total_points }
                : s
            )
          )
        }
      } catch { /* ignore parse errors */ }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
      esRef.current = null
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [connect])

  return { liveStations, connected }
}
