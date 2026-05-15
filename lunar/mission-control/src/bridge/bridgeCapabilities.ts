import type { RobotCommand } from './types'

export type BridgeMode = 'mock' | 'live'

/** Commands the live mission bridge implements today. */
export const LIVE_BRIDGE_COMMANDS = new Set<RobotCommand['type']>([
  'estop',
  'pause_autonomy',
  'manual_takeover',
  'resume_autonomy',
  'drive',
  'mark_zone',
  'set_navigation_active',
  'actuator',
  'clear_estop',
])

export function isCommandSupported(mode: BridgeMode, command: RobotCommand): boolean {
  if (mode === 'mock') return true
  return LIVE_BRIDGE_COMMANDS.has(command.type)
}

export function commandDisabledReason(mode: BridgeMode, command: RobotCommand): string | undefined {
  if (mode === 'mock') return undefined
  if (isCommandSupported(mode, command)) return undefined
  if (command.type === 'payload') {
    return 'Payload macros are not wired on the live bridge yet. Use lunar run dig / nav-dig or keyboard teleop.'
  }
  if (command.type === 'pid') return 'PID tuning is not applied from the dashboard yet.'
  if (command.type === 'save_map') return 'Save map is not implemented on the live bridge yet.'
  if (command.type === 'recording') {
    return 'Bag recording is not started from the dashboard. Use `lunar run` session logging instead.'
  }
  return 'Not available on the live bridge.'
}
