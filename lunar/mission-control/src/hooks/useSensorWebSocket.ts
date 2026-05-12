import { useEffect, useState } from 'react'
import type { LogLine, Metric, MissionControlSnapshot, SensorSnapshot, TrendPoint } from '../bridge/types'
import { parseSensorWsPayload, type ParsedSensorMessage } from './sensorWsParse'

const RECONNECT_MS = 500

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

    function connect() {
      if (closed) return
      socket = new WebSocket(`${wsBase}/sensor/ws`)

      socket.onopen = () => {
        if (!closed) setConnected(true)
      }

      socket.onmessage = (ev) => {
        if (closed || typeof ev.data !== 'string') return
        const next = parseSensorWsPayload(ev.data)
        if (next) setParsed(next)
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
      socket?.close()
    }
  }, [wsBase])

  if (!wsBase || !parsed) return null

  return {
    trends: parsed.trends,
    sensors: parsed.sensors,
    metrics: parsed.patchMetrics(snapshot.metrics),
    logs: mergeLogs(snapshot.logs, parsed.recentLogs),
    connected,
  }
}
