import { useEffect, useState } from 'react'
import type { CameraStream, StreamStatus } from '../bridge/types'

const RECONNECT_MS = 500

const cameraSocketNames: Record<CameraStream['id'], string> = {
  front: 'rgb',
  rear: 'rear',
}

export function useCameraFrame(camera: CameraStream, wsBase: string | undefined) {
  const [frameUrl, setFrameUrl] = useState<string | null>(null)
  const [socketState, setSocketState] = useState<StreamStatus>('unknown')

  useEffect(() => {
    if (!wsBase) {
      return
    }

    let closed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let socket: WebSocket | undefined
    let currentUrl: string | null = null

    function revokeCurrent() {
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl)
        currentUrl = null
      }
    }

    function connect() {
      if (closed) return
      setSocketState((prev) => (prev === 'live' ? prev : 'connecting'))
      const path = cameraSocketNames[camera.id]
      socket = new WebSocket(`${wsBase}/camera/ws/${path}`)
      socket.binaryType = 'arraybuffer'

      socket.onmessage = (event) => {
        if (closed) return
        const buf = event.data as ArrayBuffer
        const blob = new Blob([buf], { type: 'image/jpeg' })
        const nextUrl = URL.createObjectURL(blob)
        setFrameUrl(nextUrl)
        setSocketState('live')
        if (currentUrl) URL.revokeObjectURL(currentUrl)
        currentUrl = nextUrl
      }

      socket.onerror = () => {
        if (!closed) setSocketState('stale')
      }

      socket.onclose = () => {
        if (closed) return
        setSocketState('missing')
        setFrameUrl(null)
        revokeCurrent()
        reconnectTimer = window.setTimeout(connect, RECONNECT_MS)
      }
    }

    connect()

    return () => {
      closed = true
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      socket?.close()
      revokeCurrent()
      setFrameUrl(null)
    }
  }, [camera.id, wsBase])

  const effectiveFrameUrl = wsBase ? frameUrl : null
  const effectiveSocketState: StreamStatus = wsBase ? socketState : 'unknown'

  return { frameUrl: effectiveFrameUrl, socketState: effectiveSocketState, configured: Boolean(wsBase) }
}
