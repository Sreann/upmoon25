/** True when `lunar dashboard` proxies bridge WebSockets on the dashboard HTTP port. */
export function sameOriginBridgeWsEnabled(): boolean {
  if (typeof window !== 'undefined') {
    const runtimeFlag = (window as typeof window & { __LUNAR_USE_SAME_ORIGIN_WS__?: boolean })
      .__LUNAR_USE_SAME_ORIGIN_WS__
    if (runtimeFlag === true) return true
  }

  const flag = import.meta.env.VITE_USE_SAME_ORIGIN_WS
  return flag === '1' || flag === 'true'
}

function wsOriginFromPage(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

/** Mission-control WebSocket URL (`/mission/ws`). */
export function resolveMissionWsUrl(): string | undefined {
  if (
    import.meta.env.VITE_MISSION_WS_DISABLE === '1' ||
    import.meta.env.VITE_MISSION_WS_DISABLE === 'true'
  ) {
    return undefined
  }
  if (import.meta.env.VITE_FORCE_MOCK === '1' || import.meta.env.VITE_FORCE_MOCK === 'true') {
    return undefined
  }
  if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('mock') === '1') {
    return undefined
  }
  const env = (import.meta.env.VITE_MISSION_WS_URL as string | undefined)?.trim()
  if (env) return env
  if (typeof window === 'undefined') return undefined
  if (sameOriginBridgeWsEnabled()) {
    return `${wsOriginFromPage()}/mission/ws`
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.hostname}:8770/mission/ws`
}

/** Camera + sensor WebSocket base (paths `/camera/ws/*`, `/sensor/ws`). */
export function resolveCameraWsBaseUrl(): string | undefined {
  const env = (import.meta.env.VITE_CAMERA_WS_BASE_URL as string | undefined)?.trim()
  if (env) return env.replace(/\/$/, '')
  if (typeof window === 'undefined') return undefined
  const params = new URLSearchParams(window.location.search)
  if (sameOriginBridgeWsEnabled() || params.get('cameraProxy') === '1') {
    return wsOriginFromPage()
  }
  const port = ((import.meta.env.VITE_CAMERA_WS_PORT as string | undefined)?.trim() || '8767').replace(/^:/, '')
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.hostname}:${port}`
}
