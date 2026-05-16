import { useEffect, useState } from 'react'
import type { ActuatorSnapshot, LogLine, Metric, MissionControlSnapshot, SensorSnapshot, TrendPoint } from '../bridge/types'
import { parseSensorWsPayload, type ParsedSensorMessage } from './sensorWsParse'

const RECONNECT_MS = 500
const SENSOR_UI_REFRESH_MS = 200

function mergeLogs(snapshotLogs: LogLine[], recent: string[]): LogLine[] {
  if (recent.length === 0) return snapshotLogs
  const tail = recent.slice(-4).map((message, i) => ({
    ts: `ros:${i}`,
    level: 'info' as const,
    message,
  }))
  return [...tail, ...snapshotLogs].slice(0, 40)
}

export type SensorWsOverlay = {
  trends: TrendPoint[] | null
  sensors: SensorSnapshot
  actuators: Partial<ActuatorSnapshot>
  metrics: Metric[]
  logs: LogLine[]
  connected: boolean
}

/**
 * Subscribes to /sensor/ws on the same Tornado server as camera JPEG streams
 * (lunar/src/lunar/dashboard/camera_ws.py), mirroring Streamlit live telemetry.
 */
export function useSensorWebSocket(
  wsBase: string | undefined,
  snapshot: MissionControlSnapshot,
): SensorWsOverlay | null {
  const [parsed, setParsed] = useState<ParsedSensorMessage | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!wsBase) {
      return
    }

    let closed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let socket: WebSocket | undefined
    let flushTimer: ReturnType<typeof setTimeout> | undefined
    let lastFlushAt = 0
    let pendingPayload: string | null = null

    function flushLatestPayload() {
      flushTimer = undefined
      if (closed || pendingPayload === null) return
      const payload = pendingPayload
      pendingPayload = null
      const next = parseSensorWsPayload(payload)
      if (next) {
        lastFlushAt = performance.now()
        setParsed(next)
      }
    }

    function scheduleSensorUiUpdate(payload: string) {
      pendingPayload = payload
      if (flushTimer !== undefined) return
      const now = performance.now()
      const waitMs = Math.max(0, SENSOR_UI_REFRESH_MS - (now - lastFlushAt))
      if (waitMs === 0) {
        flushLatestPayload()
      } else {
        flushTimer = window.setTimeout(flushLatestPayload, waitMs)
      }
    }

    function connect() {
      if (closed) return
      socket = new WebSocket(`${wsBase}/sensor/ws`)

      socket.onopen = () => {
        if (!closed) setConnected(true)
      }

      socket.onmessage = (ev) => {
        if (closed || typeof ev.data !== 'string') return
        scheduleSensorUiUpdate(ev.data)
      }

      socket.onerror = () => {
        socket?.close()
      }

      socket.onclose = () => {
        if (closed) return
        setConnected(false)
        reconnectTimer = window.setTimeout(connect, RECONNECT_MS)
      }
    }

    connect()

    return () => {
      closed = true
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      if (flushTimer !== undefined) window.clearTimeout(flushTimer)
      socket?.close()
    }
  }, [wsBase])

  if (!wsBase || !parsed) return null

  return {
    trends: parsed.trends,
    sensors: parsed.sensors,
    actuators: parsed.actuators,
    metrics: parsed.patchMetrics(snapshot.metrics),
    logs: mergeLogs(snapshot.logs, parsed.recentLogs),
    connected,
  }
}
