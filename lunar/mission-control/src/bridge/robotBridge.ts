import { createMockSnapshot, type DemoScenario } from './mockSnapshot'
import type { CommandResult, FieldZone, MissionControlSnapshot, RobotCommand } from './types'

export type RobotBridge = {
  getSnapshot(): MissionControlSnapshot
  sendCommand(command: RobotCommand): Promise<CommandResult>
}

export class MockRobotBridge implements RobotBridge {
  private scenario: DemoScenario
  private readonly onMarkUpdate?: () => void
  private readonly zonePatches: Partial<
    Record<FieldZone['id'], Pick<FieldZone, 'status' | 'detail' | 'odom_x' | 'odom_y'>>
  > = {}
  private navigationActive = false
  private estop = false

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
    return {
      ...base,
      zones,
      mission: {
        ...base.mission,
        navigationActive: this.navigationActive,
        estop: this.estop,
        mode: this.estop ? 'Estop' : base.mission.mode,
        state: this.estop ? 'ESTOP' : base.mission.state,
      },
    }
  }

  async sendCommand(command: RobotCommand): Promise<CommandResult> {
    if (this.scenario === 'offline' && command.type !== 'estop') {
      return {
        accepted: false,
        message: 'Robot bridge is offline. Only local ESTOP UI state can be changed.',
      }
    }

    if (command.type === 'estop') {
      this.estop = true
      this.navigationActive = false
      this.onMarkUpdate?.()
      return {
        accepted: true,
        message: 'ESTOP (mock). Switch to Live bridge for robot commands.',
        commandId: crypto.randomUUID(),
      }
    }

    if (command.type === 'clear_estop') {
      this.estop = false
      this.onMarkUpdate?.()
      return { accepted: true, message: 'ESTOP cleared (mock).', commandId: crypto.randomUUID() }
    }

    if (this.estop) {
      return { accepted: false, message: 'Rejected: ESTOP is active (mock).' }
    }

    if (command.type === 'payload') {
      return {
        accepted: false,
        message:
          command.command === 'dig_start' && command.cycles
            ? `Payload macros are mock-only demos; use lunar run dig / nav-dig --dig-cycles ${command.cycles} on the robot.`
            : 'Payload macros are mock-only demos; use lunar run dig / nav-dig on the robot.',
      }
    }

    if (command.type === 'set_navigation_active') {
      this.navigationActive = command.active
      this.onMarkUpdate?.()
      return {
        accepted: true,
        message: `navigation_active = ${command.active} (mock).`,
        commandId: crypto.randomUUID(),
      }
    }

    if (command.type === 'mark_zone') {
      const zone = command.zone
      const pick = command.pick
      const snap = createMockSnapshot(this.scenario)
      const zm = snap.zoneMarking
      let odom_x: number | undefined
      let odom_y: number | undefined
      if (pick && zm) {
        const yawDeg = zm.yawDeg ?? 0
        const yaw = (yawDeg * Math.PI) / 180
        const lx = pick.x
        const ly = pick.y
        odom_x = zm.x + Math.cos(yaw) * lx - Math.sin(yaw) * ly
        odom_y = zm.y + Math.sin(yaw) * lx + Math.cos(yaw) * ly
      }
      this.zonePatches[zone] = {
        status: 'operator_marked',
        detail: pick
          ? `odom (mock) ← base_link (${pick.x.toFixed(2)},${pick.y.toFixed(2)})`
          : 'operator marked (mock)',
        ...(odom_x !== undefined ? { odom_x, odom_y } : {}),
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
