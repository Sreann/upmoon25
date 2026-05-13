export type HealthStatus = 'ok' | 'warn' | 'bad' | 'idle'

export type StreamStatus = 'live' | 'connecting' | 'stale' | 'missing' | 'unknown'

export type RobotMode = 'Manual' | 'Assisted' | 'Auto' | 'Paused' | 'Recovery' | 'Estop'

export type MissionState =
  | 'IDLE'
  | 'HEALTH_CHECK'
  | 'WAIT_FOR_ZONE_MARKS'
  | 'DISCOVER_DUMP_ZONE'
  | 'NAV_TO_DIG'
  | 'DIG'
  | 'NAV_TO_DUMP'
  | 'DUMP'
  | 'RETURN_TO_DIG'
  | 'RECOVERY'
  | 'PAUSED'
  | 'ABORTED'
  | 'ESTOP'

export type MissionSnapshot = {
  connected: boolean
  armed: boolean
  estop: boolean
  mode: RobotMode
  state: MissionState
  target: string
  heartbeatMs: number | null
  confidence: number
  cycle: number
  payload: 'empty' | 'digging' | 'loaded' | 'dumping' | 'unknown'
  stopReason: string
  lastDecision: string
  nextTransition: string
}

export type Metric = {
  label: string
  value: string
  detail?: string
  status?: HealthStatus
}

export type TopicHealth = {
  topic: string
  status: StreamStatus
  age: string
  rate: string
  note: string
  safetyCritical?: boolean
}

export type CameraStream = {
  id: 'front' | 'rear'
  name: string
  topic: string
  status: StreamStatus
  fps?: string
  resolution?: string
}

export type HardwareRow = {
  category: string
  name: string
  status: string
  detail: string
  severity: HealthStatus
}

export type ZoneStatus = 'unknown' | 'operator_marked' | 'robot_detected' | 'confirmed' | 'stale'

export type FieldZone = {
  id: 'start' | 'dig' | 'dump' | 'no_go'
  label: string
  status: ZoneStatus
  detail: string
}

/** Pose published with operator zone marks (`/autonomy/zone_mark` via mission bridge). */
export type ZoneMarkingSnapshot = {
  poseFrame: string
  odomTopic: string
  odomStatus: StreamStatus
  odomAge: string
  x: number
  y: number
  yawDeg: number | null
}

export type LogLine = {
  ts: string
  level: 'info' | 'warn' | 'error'
  message: string
}

export type TrendPoint = {
  label: string
  cpu: number
  temp: number
  battery: number
  odomVelocity: number
  commandVelocity: number
}

export type SensorSnapshot = {
  irLeft: number | null
  irRight: number | null
  encoderLeft: number | null
  encoderRight: number | null
}

export type PidGains = {
  kp: number
  ki: number
  kd: number
}

export type AuditItem = {
  label: string
  status: HealthStatus
  detail: string
}

export type TerrainGridSnapshot = {
  width: number
  height: number
  resolution: number
  frameId: string
  ageMs: number | null
  status: StreamStatus
  cells: number[]
  obstacleCells: number
  cautionCells: number
  unknownCells: number
  note: string
}

export type MissionControlSnapshot = {
  mission: MissionSnapshot
  metrics: Metric[]
  topics: TopicHealth[]
  cameras: CameraStream[]
  hardware: HardwareRow[]
  zones: FieldZone[]
  /** When omitted (older bridge), UI infers odom health from topics/hardware. */
  zoneMarking?: ZoneMarkingSnapshot
  logs: LogLine[]
  trends: TrendPoint[]
  sensors: SensorSnapshot
  pid: PidGains
  audit: AuditItem[]
  terrainGrid?: TerrainGridSnapshot
  rawConfig: string
}

export type DriveCommand = 'forward' | 'reverse' | 'left' | 'right' | 'stop'

export type PayloadCommand = 'dig_start' | 'dig_stop' | 'dump_start' | 'dump_stop' | 'stow' | 'abort'

export type RobotCommand =
  | { type: 'estop' }
  | { type: 'pause_autonomy' }
  | { type: 'resume_autonomy' }
  | { type: 'manual_takeover' }
  | { type: 'drive'; command: DriveCommand; speedLimit: number }
  | { type: 'payload'; command: PayloadCommand }
  | { type: 'mark_zone'; zone: FieldZone['id']; pick?: { frameId: 'base_link'; x: number; y: number } }
  | { type: 'recording'; enabled: boolean; name?: string }
  | { type: 'save_map'; name: string }
  | { type: 'pid'; gains: PidGains }

export type CommandResult = {
  accepted: boolean
  message: string
  commandId?: string
}
