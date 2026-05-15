import { commandDisabledReason, type BridgeMode } from './bridgeCapabilities'
import type { RobotCommand } from './types'

export function commandButtonState(
  mode: BridgeMode,
  connected: boolean,
  command: RobotCommand,
  extraDisabled?: boolean,
): { disabled: boolean; title?: string } {
  if (!connected) {
    return { disabled: true, title: 'Bridge offline' }
  }
  if (extraDisabled) {
    return { disabled: true }
  }
  const reason = commandDisabledReason(mode, command)
  if (reason) {
    return { disabled: true, title: reason }
  }
  return { disabled: false }
}
