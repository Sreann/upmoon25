import { createMockSnapshot, type DemoScenario } from './mockSnapshot'
import type { CommandResult, FieldZone, MissionControlSnapshot, RobotCommand } from './types'

export type RobotBridge = {
  getSnapshot(): MissionControlSnapshot
  sendCommand(command: RobotCommand): Promise<CommandResult>
}

export class MockRobotBridge implements RobotBridge {
  private scenario: DemoScenario
  private readonly onMarkUpdate?: () => void
  private readonly zonePatches: Partial<Record<FieldZone['id'], Pick<FieldZone, 'status' | 'detail'>>> = {}

  constructor(scenario: DemoScenario = 'degraded', onMarkUpdate?: () => void) {
    this.scenario = scenario
    this.onMarkUpdate = onMarkUpdate
  }

  setScenario(scenario: DemoScenario) {
    this.scenario = scenario
  }

  getSnapshot(): MissionControlSnapshot {
    const base = createMockSnapshot(this.scenario)
    const zones = base.zones.map((z) => ({ ...z, ...(this.zonePatches[z.id] ?? {}) }))
    return { ...base, zones }
  }

  async sendCommand(command: RobotCommand): Promise<CommandResult> {
    if (this.scenario === 'offline' && command.type !== 'estop') {
      return {
        accepted: false,
        message: 'Robot bridge is offline. Only local ESTOP UI state can be changed.',
      }
    }

    if (command.type === 'mark_zone') {
      const zone = command.zone
      const pick = command.pick
      this.zonePatches[zone] = {
        status: 'operator_marked',
        detail: pick
          ? `odom (mock) ← base_link (${pick.x.toFixed(2)},${pick.y.toFixed(2)})`
          : 'operator marked (mock)',
      }
      this.onMarkUpdate?.()
      return {
        accepted: true,
        message: pick ? `Marked ${zone} (${pick.x.toFixed(2)}, ${pick.y.toFixed(2)}).` : `Marked ${zone}.`,
        commandId: crypto.randomUUID(),
      }
    }

    if (command.type === 'drive' && command.command !== 'stop') {
      return {
        accepted: true,
        message: `Mock accepted ${command.command} at speed limit ${command.speedLimit}%. Real bridge must enforce hold heartbeat.`,
        commandId: crypto.randomUUID(),
      }
    }

    return {
      accepted: true,
      message: `Mock accepted ${command.type}.`,
      commandId: crypto.randomUUID(),
    }
  }
}
