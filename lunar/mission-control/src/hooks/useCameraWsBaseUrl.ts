import { useMemo } from 'react'

/**
 * Resolves the Tornado camera/sensor bridge base URL (Streamlit parity).
 * Prefer VITE_CAMERA_WS_BASE_URL; otherwise same hostname as the page and
 * VITE_CAMERA_WS_PORT (default 8767), matching lunar/dashboard/app.py.
 */
export function useCameraWsBaseUrl(): string | undefined {
  const env = (import.meta.env.VITE_CAMERA_WS_BASE_URL as string | undefined)?.trim()
  const port = ((import.meta.env.VITE_CAMERA_WS_PORT as string | undefined)?.trim() || '8767').replace(/^:/, '')
  return useMemo(() => {
    if (env) return env.replace(/\/$/, '')
    if (typeof window === 'undefined') return undefined
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.hostname}:${port}`
  }, [env, port])
}
