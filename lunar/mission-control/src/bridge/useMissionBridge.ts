import { useEffect, useMemo, useReducer, useState } from 'react'
import { createMockSnapshot, type DemoScenario } from './mockSnapshot'
import { LiveRobotBridgeClient, type LiveBridgeStatus } from './liveBridge'
import { MockRobotBridge } from './robotBridge'
import type { CommandResult, MissionControlSnapshot, RobotCommand } from './types'

type BridgeMode = 'mock' | 'live'

const liveUrl = import.meta.env.VITE_MISSION_WS_URL as string | undefined

export function useMissionBridge(scenario: DemoScenario) {
  const [mode, setMode] = useState<BridgeMode>(liveUrl ? 'live' : 'mock')
  const [liveSnapshot, setLiveSnapshot] = useState<MissionControlSnapshot>(() => createMockSnapshot(scenario))
  const [liveStatus, setLiveStatus] = useState<LiveBridgeStatus>({
    connected: false,
    connecting: false,
    lastError: null,
    lastMessageAt: null,
  })

  const [, bumpMock] = useReducer((x: number) => x + 1, 0)
  const mockBridge = useMemo(() => new MockRobotBridge(scenario, bumpMock), [scenario])
  const mockSnapshot = mockBridge.getSnapshot()

  const liveBridge = useMemo(() => {
    if (!liveUrl) return null
    return new LiveRobotBridgeClient({
      url: liveUrl,
      onSnapshot: setLiveSnapshot,
      onStatus: setLiveStatus,
    })
  }, [])

  useEffect(() => {
    if (mode !== 'live' || !liveBridge) return
    liveBridge.connect()
    return () => liveBridge.disconnect()
  }, [liveBridge, mode])

  async function sendCommand(command: RobotCommand): Promise<CommandResult> {
    if (mode === 'live' && liveBridge) {
      return liveBridge.sendCommand(command)
    }
    return mockBridge.sendCommand(command)
  }

  return {
    mode,
    setMode,
    snapshot: mode === 'mock' ? mockSnapshot : liveSnapshot,
    sendCommand,
    liveAvailable: Boolean(liveUrl),
    liveStatus,
    liveUrl,
  }
}
