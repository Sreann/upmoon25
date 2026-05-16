import { useEffect, useRef, useState } from 'react'
import type { CameraStream, StreamStatus } from '../bridge/types'

const RECONNECT_MS = 500

const cameraSocketNames: Record<CameraStream['id'], string> = {
  front: 'rgb',
  rear: 'rear',
}

export function useCameraFrame(camera: CameraStream, wsBase: string | undefined) {
  const imageRef = useRef<HTMLImageElement | null>(null)
  const [hasFrame, setHasFrame] = useState(false)
  const [socketState, setSocketState] = useState<StreamStatus>('unknown')

  useEffect(() => {
    if (!wsBase) {
      return
    }

    let closed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let socket: WebSocket | undefined
    let currentUrl: string | null = null
    let pendingUrl: string | null = null
    let frameRequest: number | undefined

    function revokeCurrent() {
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl)
        currentUrl = null
      }
    }

    function revokePending() {
      if (pendingUrl) {
        URL.revokeObjectURL(pendingUrl)
        pendingUrl = null
      }
    }

    function clearImage() {
      if (imageRef.current) {
        imageRef.current.removeAttribute('src')
      }
      if (frameRequest !== undefined) {
        window.cancelAnimationFrame(frameRequest)
        frameRequest = undefined
      }
      revokePending()
      revokeCurrent()
      setHasFrame(false)
    }

    function publishPendingFrame() {
      frameRequest = undefined
      if (closed || !pendingUrl) return
      const nextUrl = pendingUrl
      pendingUrl = null
      if (imageRef.current) {
        imageRef.current.src = nextUrl
      }
      setSocketState('live')
      setHasFrame((prev) => (prev ? prev : true))
      if (currentUrl) URL.revokeObjectURL(currentUrl)
      currentUrl = nextUrl
    }

    function connect() {
      if (closed) return
      setSocketState((prev) => (prev === 'live' ? prev : 'connecting'))
      const path = cameraSocketNames[camera.id]
      socket = new WebSocket(`${wsBase}/camera/ws/${path}`)
      socket.binaryType = 'blob'

      socket.onmessage = (event) => {
        if (closed) return
        const blob = event.data instanceof Blob
          ? event.data
          : new Blob([event.data as ArrayBuffer], { type: 'image/jpeg' })
        const nextUrl = URL.createObjectURL(blob)
        if (pendingUrl) {
          URL.revokeObjectURL(pendingUrl)
        }
        pendingUrl = nextUrl
        if (frameRequest === undefined) {
          frameRequest = window.requestAnimationFrame(publishPendingFrame)
        }
      }

      socket.onerror = () => {
        if (!closed) setSocketState('stale')
      }

      socket.onclose = () => {
        if (closed) return
        setSocketState('missing')
        clearImage()
        reconnectTimer = window.setTimeout(connect, RECONNECT_MS)
      }
    }

    connect()

    return () => {
      closed = true
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      socket?.close()
      clearImage()
    }
  }, [camera.id, wsBase])

  const effectiveHasFrame = wsBase ? hasFrame : false
  const effectiveSocketState: StreamStatus = wsBase ? socketState : 'unknown'

  return { imageRef, hasFrame: effectiveHasFrame, socketState: effectiveSocketState, configured: Boolean(wsBase) }
}
