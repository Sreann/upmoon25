import type { ActuatorSnapshot, HealthStatus, Metric, SensorSnapshot, TrendPoint } from '../bridge/types'

export type ParsedSensorMessage = {
  /** Null until history buffers are populated (see camera_ws `system_tick`). */
  trends: TrendPoint[] | null
  sensors: SensorSnapshot
  actuators: Partial<ActuatorSnapshot>
  recentLogs: string[]
  patchMetrics: (base: Metric[]) => Metric[]
}

function numArray(v: unknown): number[] | null {
  if (!Array.isArray(v)) return null
  const out: number[] = []
  for (const x of v) {
    const n = typeof x === 'number' ? x : Number(x)
    if (!Number.isFinite(n)) return null
    out.push(n)
  }
  return out
}

function buildTrendsFromPayload(p: Record<string, unknown>): TrendPoint[] | null {
  const cpu = numArray(p.history_cpu)
  const temp = numArray(p.history_temp)
  const battery = numArray(p.history_battery)
  const vel = numArray(p.history_vel)
  const baseVel = numArray(p.history_base_vel)
  const time = numArray(p.time)
  if (!cpu || !temp || !battery || !vel || !baseVel) return null
  const n = Math.min(cpu.length, temp.length, battery.length, vel.length, baseVel.length)
  if (n < 1) return null
  const take = Math.min(12, n)
  const start = n - take
  const trends: TrendPoint[] = []
  for (let i = start; i < n; i++) {
    const t = time && time.length > i ? time[i]! : (i - start) * 0.5
    trends.push({
      label: `${t.toFixed(2)}s`,
      cpu: Math.round(cpu[i]!),
      temp: Math.round(temp[i]!),
      battery: Number(battery[i]!.toFixed(1)),
      odomVelocity: Number(vel[i]!.toFixed(2)),
      commandVelocity: Number(baseVel[i]!.toFixed(2)),
    })
  }
  return trends
}

function asNum(v: unknown, fallback = 0): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function asInt(v: unknown): number | null {
  if (v === null || v === undefined) return null
  const n = typeof v === 'number' ? Math.trunc(v) : Math.trunc(Number(v))
  return Number.isFinite(n) ? n : null
}

export function parseSensorWsPayload(raw: string): ParsedSensorMessage | null {
  let p: Record<string, unknown>
  try {
    p = JSON.parse(raw) as Record<string, unknown>
  } catch {
    return null
  }
  const trends = buildTrendsFromPayload(p)

  const sensors: SensorSnapshot = {
    irLeft: asInt(p.ir_left),
    irRight: asInt(p.ir_right),
    encoderLeft: asInt(p.encoder_left),
    encoderRight: asInt(p.encoder_right),
    encoderPinRight: asInt(p.encoder_pin_right),
    encoderPinLeft: asInt(p.encoder_pin_left),
    encoderDecRight: asInt(p.encoder_dec_right),
    encoderDecLeft: asInt(p.encoder_dec_left),
    encoderBadRight: asInt(p.encoder_bad_right),
    encoderBadLeft: asInt(p.encoder_bad_left),
  }

  const actuators: Partial<ActuatorSnapshot> = {
    driveLinear: asNum(p.drive_linear),
    driveAngular: asNum(p.drive_angular),
    cameraHeight: asInt(p.camera_height) ?? undefined,
    panAngle: asInt(p.pan_angle) ?? undefined,
    bucketPos: asInt(p.dig_bucket_pos_commanded) ?? asInt(p.bucket_pos) ?? undefined,
    bucketPosMax: asInt(p.bucket_pos_max) ?? undefined,
    bucketVel: asInt(p.bucket_vel) ?? undefined,
    conveyor: asInt(p.conveyor) ?? undefined,
  }

  const linearVel = asNum(p.linear_vel)
  const odomX = asNum(p.odom_x)
  const odomY = asNum(p.odom_y)
  const batteryVoltage = asNum(p.battery_voltage)
  const networkLatency = asNum(p.network_latency)

  const recentLogs = Array.isArray(p.recent_logs)
    ? p.recent_logs.filter((x): x is string => typeof x === 'string')
    : []

  function patchMetrics(base: Metric[]): Metric[] {
    return base.map((m) => {
      switch (m.label) {
        case 'Linear Vel':
          return {
            ...m,
            value: `${linearVel.toFixed(2)} m/s`,
            detail: 'camera_ws /sensor/ws',
            status: 'ok' as HealthStatus,
          }
        case 'Pose':
          return {
            ...m,
            value: `${odomX.toFixed(1)}, ${odomY.toFixed(1)}`,
            detail: 'odom (camera_ws)',
            status: 'ok' as HealthStatus,
          }
        case 'Battery':
          return {
            ...m,
            value: `${batteryVoltage.toFixed(1)} V`,
            detail: 'camera_ws /sensor/ws',
            status: 'ok' as HealthStatus,
          }
        case 'Latency':
          return {
            ...m,
            value: `${Math.round(networkLatency)} ms`,
            detail: 'camera_ws ping',
            status: 'ok' as HealthStatus,
          }
        default:
          return m
      }
    })
  }

  return { trends: trends && trends.length > 0 ? trends : null, sensors, actuators, recentLogs, patchMetrics }
}
