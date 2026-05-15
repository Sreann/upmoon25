import { useMemo } from 'react'
import { resolveCameraWsBaseUrl } from '../bridge/bridgeWsUrls'

/**
 * Resolves the Tornado camera/sensor bridge base URL.
 * When `lunar dashboard` sets VITE_USE_SAME_ORIGIN_WS=1, uses the dashboard HTTP port (Vite proxy).
 */
export function useCameraWsBaseUrl(): string | undefined {
  return useMemo(() => resolveCameraWsBaseUrl(), [])
}
