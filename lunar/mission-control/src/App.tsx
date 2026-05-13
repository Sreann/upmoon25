import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Camera,
  CircleStop,
  Cpu,
  Database,
  Flag,
  Gauge,
  Home,
  MapPinned,
  Pause,
  Play,
  Power,
  Radio,
  Save,
  ShieldAlert,
  Shovel,
  SlidersHorizontal,
  Square,
  Terminal,
  Video,
  WifiOff,
} from 'lucide-react'
import { clsx } from 'clsx'
import type {
  CameraStream,
  FieldZone,
  HealthStatus,
  Metric,
  MissionControlSnapshot,
  StreamStatus,
  TerrainGridSnapshot,
} from './bridge/types'
import type { DemoScenario } from './bridge/mockSnapshot'
import { useMissionBridge } from './bridge/useMissionBridge'
import { AutonomyStateMachineChart } from './components/AutonomyStateMachineChart'
import { ZoneMarkingPanel } from './components/ZoneMarkingPanel'
import { useCameraFrame } from './hooks/useCameraFrame'
import { useCameraWsBaseUrl } from './hooks/useCameraWsBaseUrl'
import { useSensorWebSocket } from './hooks/useSensorWebSocket'

const scenarioLabels: Record<DemoScenario, string> = {
  nominal: 'Nominal',
  degraded: 'Degraded',
  offline: 'Offline',
}

function statusClass(status: HealthStatus = 'idle') {
  return {
    ok: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
    warn: 'border-amber-500/40 bg-amber-500/10 text-amber-100',
    bad: 'border-red-500/50 bg-red-500/10 text-red-100',
    idle: 'border-slate-700 bg-slate-900/70 text-slate-200',
  }[status]
}

function streamToStatus(status: StreamStatus): HealthStatus {
  const statuses: Record<StreamStatus, HealthStatus> = {
    live: 'ok',
    connecting: 'warn',
    stale: 'warn',
    missing: 'bad',
    unknown: 'idle',
  }
  return statuses[status]
}

function Panel({
  title,
  icon,
  children,
  className,
  action,
}: {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}) {
  return (
    <section className={clsx('rounded-lg border border-slate-800 bg-slate-950/80 shadow-xl shadow-black/10', className)}>
      <div className="flex min-h-11 items-center justify-between gap-3 border-b border-slate-800 px-4 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
          {icon}
          <span>{title}</span>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

function Button({
  children,
  intent = 'default',
  className,
  disabled,
  onClick,
}: {
  children: React.ReactNode
  intent?: 'default' | 'danger' | 'safe' | 'warn'
  className?: string
  disabled?: boolean
  onClick?: () => void
}) {
  const styles = {
    default: 'border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800',
    danger: 'border-red-500/60 bg-red-600 text-white hover:bg-red-500',
    safe: 'border-emerald-500/50 bg-emerald-600/90 text-white hover:bg-emerald-500',
    warn: 'border-amber-500/50 bg-amber-500/90 text-slate-950 hover:bg-amber-400',
  }
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={clsx(
        'inline-flex min-h-9 items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45',
        styles[intent],
        className,
      )}
    >
      {children}
    </button>
  )
}

function MetricCard({ metric }: { metric: Metric }) {
  return (
    <div className={clsx('min-w-0 rounded-md border p-3', statusClass(metric.status))}>
      <div className="text-[11px] uppercase tracking-wide opacity-75">{metric.label}</div>
      <div className="mt-1 break-words text-xl font-semibold text-white">{metric.value}</div>
      {metric.detail ? <div className="mt-1 break-words text-xs opacity-75">{metric.detail}</div> : null}
    </div>
  )
}

function AlertDot({ status }: { status: HealthStatus }) {
  return <span className={clsx('h-2.5 w-2.5 rounded-full', status === 'ok' ? 'bg-emerald-300' : status === 'warn' ? 'bg-amber-300' : status === 'bad' ? 'bg-red-300' : 'bg-slate-500')} />
}

function EmptyState({ title, detail, status = 'idle' }: { title: string; detail: string; status?: HealthStatus }) {
  return (
    <div className={clsx('rounded-md border p-3 text-sm', statusClass(status))}>
      <div className="flex items-center gap-2 font-semibold text-white">
        {status === 'bad' ? <WifiOff className="h-4 w-4" /> : <AlertDot status={status} />}
        {title}
      </div>
      <div className="mt-1 text-xs opacity-80">{detail}</div>
    </div>
  )
}

function SafetyBar({
  snapshot,
  scenario,
  setScenario,
  bridgeMode,
  setBridgeMode,
  liveAvailable,
}: {
  snapshot: MissionControlSnapshot
  scenario: DemoScenario
  setScenario: (scenario: DemoScenario) => void
  bridgeMode: 'mock' | 'live'
  setBridgeMode: (mode: 'mock' | 'live') => void
  liveAvailable: boolean
}) {
  const { mission } = snapshot
  return (
    <div className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/95 px-3 py-3 backdrop-blur sm:px-4">
      <div className="mx-auto flex max-w-[1800px] flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
          <ShieldAlert className="h-5 w-5 text-amber-300" />
          Lunar Mission Control
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={clsx('rounded-full border px-2 py-1', statusClass(mission.connected ? 'ok' : 'bad'))}>Bridge {mission.connected ? 'online' : 'offline'}</span>
          <span className={clsx('rounded-full border px-2 py-1', statusClass(mission.armed ? 'warn' : 'idle'))}>{mission.armed ? 'Armed' : 'Disarmed'}</span>
          <span className={clsx('rounded-full border px-2 py-1', statusClass(mission.estop ? 'bad' : 'ok'))}>E-stop {mission.estop ? 'active' : 'clear'}</span>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1">Mode {mission.mode}</span>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1">State {mission.state}</span>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1">Heartbeat {mission.heartbeatMs === null ? '--' : `${mission.heartbeatMs} ms`}</span>
        </div>
        <select
          value={scenario}
          onChange={(event) => setScenario(event.target.value as DemoScenario)}
          disabled={bridgeMode === 'live'}
          className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100"
          aria-label="Demo scenario"
        >
          {Object.entries(scenarioLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={bridgeMode}
          onChange={(event) => setBridgeMode(event.target.value as 'mock' | 'live')}
          className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100"
          aria-label="Bridge mode"
        >
          <option value="mock">Mock bridge</option>
          <option value="live" disabled={!liveAvailable}>Live bridge</option>
        </select>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button intent="danger" className="min-w-28">
            <Power className="h-4 w-4" /> ESTOP
          </Button>
          <Button intent="warn" disabled={!mission.connected}>
            <Pause className="h-4 w-4" /> Pause
          </Button>
          <Button intent="safe" disabled={!mission.connected}>
            <Play className="h-4 w-4" /> Resume
          </Button>
          <Button disabled={!mission.connected}>
            <CircleStop className="h-4 w-4" /> Manual Takeover
          </Button>
        </div>
      </div>
    </div>
  )
}

function CameraFeed({ camera, wsBase }: { camera: CameraStream; wsBase: string | undefined }) {
  const { frameUrl, socketState, configured } = useCameraFrame(camera, wsBase)
  const tryWs = Boolean(configured)
  const displayStatus = tryWs ? socketState : camera.status
  const activeFrameUrl = tryWs && socketState === 'live' ? frameUrl : null
  const statusText = {
    live: 'live',
    connecting: 'connecting',
    stale: 'stale frame',
    missing: 'no stream',
    unknown: 'unknown',
  }[displayStatus]
  const detail = {
    live: activeFrameUrl ? 'Receiving JPEG frames from camera_ws (Tornado)' : 'WebSocket open; waiting for first JPEG',
    connecting: 'Connecting to camera WebSocket (auto-retry every 500 ms)',
    stale: 'WebSocket error; retrying',
    missing: configured ? 'Camera WebSocket closed or unreachable; retrying' : 'Could not resolve WebSocket base URL for this page',
    unknown: 'Camera has not been checked in this session',
  }[displayStatus]
  const accent = camera.id === 'front' ? 'border-orange-300' : camera.id === 'rear' ? 'border-sky-300' : 'border-slate-400'

  return (
    <div className="overflow-hidden rounded-md border border-slate-800 bg-slate-900">
      <div className="relative aspect-video bg-[radial-gradient(circle_at_40%_35%,#334155,#0f172a_42%,#020617)]">
        {activeFrameUrl ? (
          <img className="h-full w-full object-cover" src={activeFrameUrl} alt={`${camera.name} live camera feed`} />
        ) : displayStatus === 'live' ? (
          <>
            <div className={clsx('absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border-2', accent)} />
            <div className="absolute bottom-4 left-4 right-4 h-px bg-white/30" />
            <div className="absolute bottom-4 left-1/2 top-4 w-px bg-white/30" />
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <div className="max-w-xs rounded-md border border-slate-700 bg-black/60 p-4 text-center">
              <div className="text-sm font-semibold text-white">{statusText}</div>
              <div className="mt-1 text-xs text-slate-300">{detail}</div>
            </div>
          </div>
        )}
        <div className={clsx('absolute left-4 top-4 rounded border px-2 py-1 text-xs', statusClass(streamToStatus(displayStatus)))}>{statusText}</div>
      </div>
      <div className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-slate-300">
        <span>{camera.name}</span>
        <span>{camera.fps ?? '--'} FPS | {camera.resolution ?? '--'}</span>
      </div>
      <div className="border-t border-slate-800 px-3 py-2 font-mono text-[11px] text-slate-500">{camera.topic}</div>
    </div>
  )
}

const TERRAIN_PIXEL: Record<'ok' | 'warn' | 'bad' | 'unknown' | 'robot', string> = {
  ok: 'rgba(16, 185, 129, 0.42)',
  warn: 'rgba(251, 191, 36, 0.78)',
  bad: 'rgba(239, 68, 68, 0.88)',
  unknown: 'rgba(51, 65, 85, 0.95)',
  robot: 'rgba(103, 232, 249, 0.95)',
}

function classifyTerrainCell(
  cell: number,
  x: number,
  y: number,
  width: number,
): keyof typeof TERRAIN_PIXEL {
  const centerX = Math.floor(width / 2)
  if ((x === centerX || x === centerX - 1) && y < 2) return 'robot'
  if (cell >= 90) return 'bad'
  if (cell > 0) return 'warn'
  if (cell < 0) return 'unknown'
  return 'ok'
}

function fallbackTerrainCategory(x: number, y: number, w: number, h: number): keyof typeof TERRAIN_PIXEL {
  const x12 = Math.min(11, Math.floor((x * 12) / w))
  const y12 = Math.min(11, Math.floor((y * 12) / h))
  if ((x12 === 5 || x12 === 6) && y12 > 7) return 'robot'
  if ((x12 > 7 && y12 < 4) || (x12 === 2 && y12 === 5) || (x12 === 3 && y12 === 5)) return 'bad'
  if ((x12 < 3 && y12 < 3) || (x12 > 9 && y12 > 8)) return 'unknown'
  if (x12 === 7 && y12 === 6) return 'warn'
  return 'ok'
}

function TerrainGrid({
  grid,
  pickArmed,
  pickEnabled,
  onPick,
}: {
  grid?: TerrainGridSnapshot
  pickArmed?: boolean
  pickEnabled?: boolean
  onPick?: (p: { x: number; y: number }) => void
}) {
  const hasLiveCells = Boolean(grid && grid.width > 0 && grid.height > 0 && grid.cells.length === grid.width * grid.height)
  const width = hasLiveCells ? grid!.width : 30
  const height = hasLiveCells ? grid!.height : 30
  const resolutionM = hasLiveCells ? grid!.resolution : 0.1
  const categories = useMemo(() => {
    if (hasLiveCells) {
      return grid!.cells.map((cell, index) => {
        const x = index % width
        const y = Math.floor(index / width)
        return classifyTerrainCell(cell, x, y, width)
      })
    }
    return Array.from({ length: width * height }, (_, index) => {
      const x = index % width
      const y = Math.floor(index / width)
      return fallbackTerrainCategory(x, y, width, height)
    })
  }, [grid, hasLiveCells, height, width])

  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    canvas.width = width
    canvas.height = height
    ctx.imageSmoothingEnabled = false
    for (let i = 0; i < categories.length; i++) {
      const x = i % width
      const y = Math.floor(i / width)
      const cat = categories[i]!
      ctx.fillStyle = TERRAIN_PIXEL[cat]
      ctx.fillRect(x, y, 1, 1)
    }
  }, [categories, height, width])

  function clickCanvas(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!pickArmed || !pickEnabled || !onPick) return
    const canvas = e.currentTarget
    const rect = canvas.getBoundingClientRect()
    const fx = (e.clientX - rect.left) / Math.max(rect.width, 1e-6)
    const fy = (e.clientY - rect.top) / Math.max(rect.height, 1e-6)
    const ix = Math.min(width - 1, Math.max(0, Math.floor(fx * width)))
    const iy = Math.min(height - 1, Math.max(0, Math.floor(fy * height)))
    const widthM = width * resolutionM
    const lx = (iy + 0.5) * resolutionM
    const ly = -widthM / 2 + (ix + 0.5) * resolutionM
    onPick({ x: lx, y: ly })
  }

  const picking = Boolean(pickArmed && pickEnabled && onPick)

  return (
    <div className="mx-auto w-full max-w-[200px] space-y-2 sm:max-w-[220px] md:mx-0">
      <div
        className={clsx(
          'rounded-md border bg-slate-950 p-1.5 sm:p-2',
          picking ? 'cursor-crosshair border-amber-500/60 ring-1 ring-amber-500/40' : 'border-slate-800',
        )}
      >
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="Local terrain traversability grid"
          className={clsx('aspect-square h-auto w-full [image-rendering:pixelated]', picking && 'cursor-crosshair')}
          onClick={clickCanvas}
        />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
        <span>{hasLiveCells ? `${width}×${height} @ ${grid!.resolution.toFixed(2)} m/cell` : `mock ${width}×${height} @ 0.10 m/cell`}</span>
        <span>{hasLiveCells ? `${grid!.status}, age ${grid!.ageMs ?? '--'} ms` : 'waiting for /autonomy/local_terrain_grid'}</span>
      </div>
    </div>
  )
}

function MiniTrend({
  title,
  values,
  suffix = '',
}: {
  title: string
  values: number[]
  suffix?: string
}) {
  const max = Math.max(...values, 1)
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900 p-3">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{title}</span>
        <span>{values.at(-1) ?? 0}{suffix}</span>
      </div>
      <div className="mt-3 flex h-20 items-end gap-1">
        {values.map((value, index) => (
          <div
            key={`${title}-${index}`}
            className="flex-1 rounded-t bg-cyan-400/70"
            style={{ height: `${Math.max(8, (value / max) * 100)}%` }}
          />
        ))}
      </div>
    </div>
  )
}

function IrRadar({ left, right }: { left: number | null; right: number | null }) {
  const leftPct = left === null ? 0 : Math.min(100, (left / 1024) * 100)
  const rightPct = right === null ? 0 : Math.min(100, (right / 1024) * 100)
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">IR proximity radar</div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>Left</span>
            <span>{left ?? '--'}</span>
          </div>
          <div className="h-3 overflow-hidden rounded bg-slate-800">
            <div className="h-full bg-amber-300" style={{ width: `${leftPct}%` }} />
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>Right</span>
            <span>{right ?? '--'}</span>
          </div>
          <div className="h-3 overflow-hidden rounded bg-slate-800">
            <div className="h-full bg-amber-300" style={{ width: `${rightPct}%` }} />
          </div>
        </div>
      </div>
      <div className="mt-3 flex h-28 items-end justify-center gap-16 rounded border border-slate-800 bg-slate-950 p-3">
        <div className="h-20 w-8 origin-bottom -rotate-45 rounded-t-full bg-amber-400/60" style={{ transform: `rotate(-45deg) scaleY(${Math.max(0.18, leftPct / 100)})` }} />
        <div className="h-20 w-8 origin-bottom rotate-45 rounded-t-full bg-amber-400/60" style={{ transform: `rotate(45deg) scaleY(${Math.max(0.18, rightPct / 100)})` }} />
      </div>
    </div>
  )
}

function MissionOverview({ snapshot }: { snapshot: MissionControlSnapshot }) {
  const { mission } = snapshot
  return (
    <Panel title="Mission State" icon={<Activity className="h-4 w-4 text-cyan-300" />}>
      <div className="grid gap-3 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-2xl font-semibold text-white sm:text-3xl">{mission.state}</div>
            <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-xs text-amber-100">{mission.mode}</span>
          </div>
          <p className="mt-2 text-sm text-slate-300">{mission.stopReason}</p>
          <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div className="rounded border border-slate-800 bg-slate-900 p-3">
              <div className="text-xs text-slate-500">Last decision</div>
              <div className="mt-1 text-slate-100">{mission.lastDecision}</div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-900 p-3">
              <div className="text-xs text-slate-500">Next transition</div>
              <div className="mt-1 text-slate-100">{mission.nextTransition}</div>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <MetricCard metric={{ label: 'Confidence', value: `${mission.confidence}%`, detail: 'mission', status: mission.confidence > 85 ? 'ok' : mission.confidence > 0 ? 'warn' : 'bad' }} />
          <MetricCard metric={{ label: 'Payload', value: mission.payload, detail: 'bucket', status: 'idle' }} />
          <MetricCard metric={{ label: 'Cycle', value: String(mission.cycle), detail: 'dig/dump', status: 'idle' }} />
        </div>
      </div>
    </Panel>
  )
}

function FallbackDiagnostics({ snapshot }: { snapshot: MissionControlSnapshot }) {
  return (
    <Panel title="Connection And Data Fallbacks" icon={<WifiOff className="h-4 w-4 text-amber-300" />}>
      <div className="grid gap-3 lg:grid-cols-3">
        <EmptyState title="Robot bridge fallback" detail="If the bridge disconnects, freeze telemetry, disable motion buttons, and keep ESTOP visible." status={snapshot.mission.connected ? 'ok' : 'bad'} />
        <EmptyState title="No camera stream fallback" detail="Show a clear no-stream panel with topic name, stream age, and reconnect status." status={snapshot.cameras.some((camera) => camera.status === 'missing') ? 'bad' : 'ok'} />
        <EmptyState title="ROS topic stale fallback" detail="Any stale safety-critical topic should show age/rate and block autonomous start." status={snapshot.topics.some((topic) => topic.safetyCritical && topic.status !== 'live') ? 'warn' : 'ok'} />
      </div>
      <div className="mt-4 overflow-x-auto rounded-md border border-slate-800">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-slate-900 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Topic</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Age</th>
              <th className="px-3 py-2">Rate</th>
              <th className="px-3 py-2">Note</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.topics.map((row) => {
              const status = streamToStatus(row.status)
              return (
                <tr key={row.topic} className="border-t border-slate-800 bg-slate-950">
                  <td className="px-3 py-2 font-mono text-xs text-slate-100">{row.topic}</td>
                  <td className="px-3 py-2">
                    <span className={clsx('inline-flex rounded border px-2 py-1 text-xs', statusClass(status))}>{row.status}</span>
                  </td>
                  <td className="px-3 py-2 text-slate-400">{row.age}</td>
                  <td className="px-3 py-2 text-slate-400">{row.rate}</td>
                  <td className="px-3 py-2 text-slate-400">{row.note}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function App() {
  const [scenario, setScenarioState] = useState<DemoScenario>('degraded')
  const [commandStatus, setCommandStatus] = useState('No command sent in this session.')
  const [bagName, setBagName] = useState('mission_data')
  const [mapName, setMapName] = useState('lunar_field')
  const [pid, setPid] = useState({ kp: 1.0, ki: 0.0, kd: 0.1 })
  const [zoneArm, setZoneArm] = useState<FieldZone['id'] | null>(null)

  function setScenario(next: DemoScenario) {
    setZoneArm(null)
    setScenarioState(next)
  }

  const { mode, setMode: setBridgeModeInternal, snapshot, sendCommand, liveAvailable, liveStatus, liveUrl } = useMissionBridge(scenario)

  const cameraWsBase = useCameraWsBaseUrl()
  const sensorOverlay = useSensorWebSocket(cameraWsBase, snapshot)
  const displaySnapshot = useMemo(() => {
    if (!sensorOverlay) return snapshot
    return {
      ...snapshot,
      trends: sensorOverlay.trends ?? snapshot.trends,
      sensors: sensorOverlay.sensors,
      metrics: sensorOverlay.metrics,
      logs: sensorOverlay.logs,
    }
  }, [snapshot, sensorOverlay])

  function setMode(next: 'mock' | 'live') {
    setZoneArm(null)
    setBridgeModeInternal(next)
  }

  const motionDisabled = !displaySnapshot.mission.connected

  const odomLive =
    displaySnapshot.zoneMarking?.odomStatus === 'live' ||
    displaySnapshot.topics.some((t) => t.topic === '/odom' && t.status === 'live')
  const canZonePick = displaySnapshot.mission.connected && odomLive && !motionDisabled

  async function runCommand(command: Parameters<typeof sendCommand>[0]) {
    const result = await sendCommand(command)
    setCommandStatus(`${result.accepted ? 'Accepted' : 'Rejected'}: ${result.message}`)
  }

  return (
    <div className="min-h-screen bg-[#080b10] text-slate-200">
      <SafetyBar
        snapshot={displaySnapshot}
        scenario={scenario}
        setScenario={setScenario}
        bridgeMode={mode}
        setBridgeMode={setMode}
        liveAvailable={liveAvailable}
      />
      <main className="mx-auto flex max-w-[1800px] flex-col gap-4 px-3 py-4 sm:px-4">
        {mode === 'live' ? (
          <EmptyState
            title={liveStatus.connected ? 'Live bridge connected' : liveStatus.connecting ? 'Live bridge connecting' : 'Live bridge disconnected'}
            detail={liveUrl ? `${liveUrl}${liveStatus.lastError ? ` | ${liveStatus.lastError}` : ''}` : 'Set VITE_MISSION_WS_URL to enable live mode.'}
            status={liveStatus.connected ? 'ok' : liveStatus.connecting ? 'warn' : 'bad'}
          />
        ) : null}
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          {displaySnapshot.metrics.map((metric) => (
            <MetricCard key={metric.label} metric={metric} />
          ))}
        </section>

        <MissionOverview snapshot={displaySnapshot} />
        <EmptyState title="Latest command result" detail={commandStatus} status={commandStatus.startsWith('Rejected') ? 'bad' : commandStatus.startsWith('Accepted') ? 'ok' : 'idle'} />
        <FallbackDiagnostics snapshot={displaySnapshot} />

        <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <Panel
            title="Live Cameras"
            icon={<Video className="h-4 w-4 text-cyan-300" />}
            action={
              <span className="text-xs text-slate-500">
                {cameraWsBase
                  ? `${cameraWsBase} · /camera/ws/*${sensorOverlay && !sensorOverlay.connected ? ' · /sensor/ws reconnecting' : ''}`
                  : 'Resolving camera bridge URL (same host, port from VITE_CAMERA_WS_PORT or 8767)…'}
              </span>
            }
          >
            <div className="grid gap-3 lg:grid-cols-3">
              {displaySnapshot.cameras.map((camera) => (
                <CameraFeed key={camera.id} camera={camera} wsBase={cameraWsBase} />
              ))}
            </div>
          </Panel>

          <Panel title="Local Terrain And Navigation" icon={<MapPinned className="h-4 w-4 text-emerald-300" />}>
            <div className="grid gap-4 md:grid-cols-[minmax(0,220px)_1fr] md:items-start">
              <div className="space-y-1.5">
                {zoneArm ? <p className="text-center text-xs text-amber-200">Click map</p> : null}
                <TerrainGrid
                  grid={displaySnapshot.terrainGrid}
                  pickArmed={zoneArm !== null}
                  pickEnabled={canZonePick}
                  onPick={(p) => {
                    if (!zoneArm) return
                    void (async () => {
                      const result = await sendCommand({
                        type: 'mark_zone',
                        zone: zoneArm,
                        pick: { frameId: 'base_link', x: p.x, y: p.y },
                      })
                      setCommandStatus(`${result.accepted ? 'Accepted' : 'Rejected'}: ${result.message}`)
                      setZoneArm(null)
                    })()
                  }}
                />
              </div>
              <div className="min-w-0 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <MetricCard metric={{ label: 'Obstacles', value: displaySnapshot.terrainGrid ? String(displaySnapshot.terrainGrid.obstacleCells) : '--', detail: displaySnapshot.terrainGrid?.note ?? 'terrain grid', status: displaySnapshot.terrainGrid?.status === 'live' ? 'ok' : displaySnapshot.terrainGrid ? 'warn' : 'bad' }} />
                  <MetricCard metric={{ label: 'Pothole risk', value: displaySnapshot.terrainGrid ? String(displaySnapshot.terrainGrid.cautionCells) : '--', detail: 'caution cells', status: displaySnapshot.terrainGrid && displaySnapshot.terrainGrid.cautionCells > 0 ? 'warn' : displaySnapshot.terrainGrid ? 'ok' : 'bad' }} />
                  <MetricCard metric={{ label: 'Unknown cells', value: displaySnapshot.terrainGrid ? String(displaySnapshot.terrainGrid.unknownCells) : '--', detail: displaySnapshot.terrainGrid?.frameId ?? 'base_link', status: displaySnapshot.terrainGrid && displaySnapshot.terrainGrid.unknownCells > 0 ? 'warn' : displaySnapshot.terrainGrid ? 'ok' : 'bad' }} />
                  <MetricCard metric={{ label: 'Steering', value: scenario === 'nominal' ? 'forward' : 'hold', detail: scenario === 'nominal' ? 'short segment' : 'no target', status: scenario === 'nominal' ? 'ok' : 'idle' }} />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button disabled={motionDisabled}>Clear Map</Button>
                  <Button disabled={motionDisabled}>Freeze</Button>
                  <Button disabled={motionDisabled}>Toggle Hazards</Button>
                </div>
              </div>
            </div>
          </Panel>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1fr_1.2fr_1fr]">
          <Panel title="Zone marking" icon={<Flag className="h-4 w-4 text-orange-300" />}>
            <ZoneMarkingPanel snapshot={displaySnapshot} armedZone={zoneArm} onArm={setZoneArm} canArm={canZonePick} />
          </Panel>

          <Panel title="Manual Teleop" icon={<Gauge className="h-4 w-4 text-cyan-300" />}>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <div className="grid grid-cols-3 gap-2">
                  <div />
                  <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'drive', command: 'forward', speedLimit: 30 })}><ArrowUp className="h-4 w-4" /> Fwd</Button>
                  <div />
                  <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'drive', command: 'left', speedLimit: 30 })}><ArrowLeft className="h-4 w-4" /> Left</Button>
                  <Button intent="danger" onClick={() => void runCommand({ type: 'drive', command: 'stop', speedLimit: 0 })}><Square className="h-4 w-4" /> Stop</Button>
                  <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'drive', command: 'right', speedLimit: 30 })}>Right <ArrowRight className="h-4 w-4" /></Button>
                  <div />
                  <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'drive', command: 'reverse', speedLimit: 30 })}><ArrowDown className="h-4 w-4" /> Rev</Button>
                  <div />
                </div>
                <div className="mt-3">
                  <label className="text-xs text-slate-500">Speed limit</label>
                  <input disabled={motionDisabled} className="mt-1 w-full accent-cyan-400 disabled:opacity-40" type="range" min="0" max="100" defaultValue="30" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <Button disabled={motionDisabled}><Camera className="h-4 w-4" /> Pan Left</Button>
                <Button disabled={motionDisabled}>Pan Right</Button>
                <Button disabled={motionDisabled}>Cam Up</Button>
                <Button disabled={motionDisabled}>Cam Down</Button>
                <Button disabled={motionDisabled}>Bucket Up</Button>
                <Button disabled={motionDisabled}>Bucket Down</Button>
                <Button disabled={motionDisabled}>Chain Fwd</Button>
                <Button disabled={motionDisabled}>Chain Rev</Button>
                <Button disabled={motionDisabled} className="col-span-2">Conveyor Toggle</Button>
              </div>
            </div>
          </Panel>

          <Panel title="Mining Cycle" icon={<Shovel className="h-4 w-4 text-amber-300" />}>
            <div className="grid gap-2">
              <MetricCard metric={{ label: 'Macro', value: 'none', detail: 'payload idle', status: 'idle' }} />
              <div className="grid grid-cols-2 gap-2">
                <Button disabled={motionDisabled} intent="safe" onClick={() => void runCommand({ type: 'payload', command: 'dig_start' })}>Start Dig</Button>
                <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'payload', command: 'dig_stop' })}>Stop Dig</Button>
                <Button disabled={motionDisabled} intent="safe" onClick={() => void runCommand({ type: 'payload', command: 'dump_start' })}>Start Dump</Button>
                <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'payload', command: 'dump_stop' })}>Stop Dump</Button>
                <Button disabled={motionDisabled} onClick={() => void runCommand({ type: 'payload', command: 'stow' })}><Home className="h-4 w-4" /> Stow</Button>
                <Button disabled={motionDisabled} intent="danger" onClick={() => void runCommand({ type: 'payload', command: 'abort' })}>Abort Payload</Button>
              </div>
              <label className="text-xs text-slate-500">Dig duration</label>
              <input disabled={motionDisabled} className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm disabled:opacity-40" defaultValue="8 s" />
            </div>
          </Panel>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <Panel title="Analytics And Pulse" icon={<BarChart3 className="h-4 w-4 text-cyan-300" />}>
            <div className="grid gap-3 lg:grid-cols-3">
              <MiniTrend title="CPU load" values={displaySnapshot.trends.map((point) => point.cpu)} suffix="%" />
              <MiniTrend title="CPU temp" values={displaySnapshot.trends.map((point) => point.temp)} suffix=" C" />
              <MiniTrend title="Battery" values={displaySnapshot.trends.map((point) => point.battery)} suffix=" V" />
            </div>
            <div className="mt-3 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
              <div className="rounded-md border border-slate-800 bg-slate-900 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">Odometry vs command velocity</div>
                <div className="mt-3 grid grid-cols-12 items-end gap-1">
                  {displaySnapshot.trends.map((point) => (
                    <div key={point.label} className="flex h-24 flex-col justify-end gap-1">
                      <div className="rounded-t bg-purple-400/70" style={{ height: `${Math.max(6, point.odomVelocity * 300)}px` }} title={`odom ${point.odomVelocity}`} />
                      <div className="rounded-t bg-cyan-300/80" style={{ height: `${Math.max(6, point.commandVelocity * 300)}px` }} title={`cmd ${point.commandVelocity}`} />
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex gap-4 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded bg-purple-400" /> odom</span>
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded bg-cyan-300" /> command</span>
                </div>
              </div>
              <IrRadar left={displaySnapshot.sensors.irLeft} right={displaySnapshot.sensors.irRight} />
            </div>
          </Panel>

          <Panel title="Sensor And Hardware Health" icon={<Cpu className="h-4 w-4 text-cyan-300" />}>
            <div className="overflow-x-auto rounded-md border border-slate-800">
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead className="bg-slate-900 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Category</th>
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {displaySnapshot.hardware.map((row) => (
                    <tr key={row.name} className="border-t border-slate-800 bg-slate-950">
                      <td className="px-3 py-2 text-slate-400">{row.category}</td>
                      <td className="px-3 py-2 text-slate-100">{row.name}</td>
                      <td className="px-3 py-2"><span className={clsx('rounded border px-2 py-1 text-xs', statusClass(row.severity))}>{row.status}</span></td>
                      <td className="px-3 py-2 text-slate-400">{row.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Data, Logs, And Diagnostics" icon={<Database className="h-4 w-4 text-emerald-300" />}>
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-slate-500">
                    Bag name
                    <input
                      value={bagName}
                      onChange={(event) => setBagName(event.target.value)}
                      className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100"
                    />
                  </label>
                  <label className="text-xs text-slate-500">
                    Map name
                    <input
                      value={mapName}
                      onChange={(event) => setMapName(event.target.value)}
                      className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100"
                    />
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Button disabled={!displaySnapshot.mission.connected} intent="danger" onClick={() => void runCommand({ type: 'recording', enabled: true, name: bagName })}>Start Bag</Button>
                  <Button disabled={!displaySnapshot.mission.connected} onClick={() => void runCommand({ type: 'recording', enabled: false })}>Stop Bag</Button>
                  <Button disabled={!displaySnapshot.mission.connected} onClick={() => void runCommand({ type: 'save_map', name: mapName })}><Save className="h-4 w-4" /> Save Map</Button>
                  <Button disabled={!displaySnapshot.mission.connected}>Event Marker</Button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <MetricCard metric={{ label: 'CPU', value: displaySnapshot.mission.connected ? '29%' : '--', detail: 'demo', status: displaySnapshot.mission.connected ? 'ok' : 'bad' }} />
                  <MetricCard metric={{ label: 'Temp', value: displaySnapshot.mission.connected ? '54 C' : '--', detail: 'Jetson', status: displaySnapshot.mission.connected ? 'ok' : 'bad' }} />
                  <MetricCard metric={{ label: 'WiFi', value: displaySnapshot.mission.connected ? '18 ms' : '--', detail: 'ping', status: displaySnapshot.mission.connected ? 'ok' : 'bad' }} />
                  <MetricCard metric={{ label: 'Disk', value: displaySnapshot.mission.connected ? '72 GB' : '--', detail: 'bags', status: displaySnapshot.mission.connected ? 'ok' : 'bad' }} />
                </div>
              </div>
              <div className="rounded-md border border-slate-800 bg-black p-3 font-mono text-xs text-emerald-200">
                {displaySnapshot.logs.map((line) => (
                  <div key={`${line.ts}-${line.message}`} className={clsx(line.level === 'error' && 'text-red-300', line.level === 'warn' && 'text-amber-200')}>
                    {line.ts} {line.message}
                  </div>
                ))}
              </div>
            </div>
          </Panel>
        </section>

        <Panel title="Autonomy state machine" icon={<Activity className="h-4 w-4 text-cyan-300" />}>
          <AutonomyStateMachineChart current={displaySnapshot.mission.state} />
        </Panel>

        <section className="grid gap-4 xl:grid-cols-2">
          <Panel title="Localization And SLAM" icon={<Radio className="h-4 w-4 text-purple-300" />}>
            <div className="grid grid-cols-2 gap-2">
              <MetricCard metric={{ label: 'Pose source', value: scenario === 'nominal' ? 'T265' : 'none', detail: scenario === 'nominal' ? 'provisional' : 'audit needed', status: scenario === 'nominal' ? 'ok' : 'warn' }} />
              <MetricCard metric={{ label: 'T265', value: scenario === 'nominal' ? 'live' : 'unknown', detail: 'field check', status: scenario === 'nominal' ? 'ok' : 'warn' }} />
              <MetricCard metric={{ label: 'Encoders', value: 'bad data', detail: 'needs fix', status: 'bad' }} />
              <MetricCard metric={{ label: 'SLAM', value: scenario === 'nominal' ? 'evaluating' : 'not ready', detail: 'evaluate', status: 'warn' }} />
            </div>
          </Panel>
          <Panel title="Advanced Controls" icon={<Terminal className="h-4 w-4 text-slate-300" />}>
            <div className="grid grid-cols-2 gap-2">
              <Button disabled={!displaySnapshot.mission.connected}>Restart Mapper</Button>
              <Button disabled={!displaySnapshot.mission.connected}>Restart Bridge</Button>
              <Button disabled={!displaySnapshot.mission.connected}>Apply PID</Button>
              <Button>Open Foxglove</Button>
            </div>
            <div className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
              Restart and tuning actions require confirmation before they affect the robot.
            </div>
          </Panel>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr]">
          <Panel title="PID Tuning" icon={<SlidersHorizontal className="h-4 w-4 text-cyan-300" />}>
            <div className="space-y-3">
              {(['kp', 'ki', 'kd'] as const).map((key) => (
                <label key={key} className="block text-sm">
                  <div className="mb-1 flex justify-between text-xs uppercase text-slate-500">
                    <span>{key}</span>
                    <span>{pid[key].toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={key === 'kp' ? 10 : 5}
                    step={key === 'kp' ? 0.1 : 0.01}
                    value={pid[key]}
                    disabled={!displaySnapshot.mission.connected}
                    onChange={(event) => setPid((current) => ({ ...current, [key]: Number(event.target.value) }))}
                    className="w-full accent-cyan-400 disabled:opacity-40"
                  />
                </label>
              ))}
              <Button disabled={!displaySnapshot.mission.connected} onClick={() => void runCommand({ type: 'pid', gains: pid })}>Apply Gains</Button>
            </div>
          </Panel>

          <Panel title="Field Audit Checklist" icon={<ShieldAlert className="h-4 w-4 text-amber-300" />}>
            <div className="space-y-2">
              {displaySnapshot.audit.map((item) => (
                <div key={item.label} className={clsx('rounded border p-2 text-sm', statusClass(item.status))}>
                  <div className="flex items-center gap-2 font-semibold text-white">
                    <AlertDot status={item.status} />
                    {item.label}
                  </div>
                  <div className="mt-1 text-xs opacity-80">{item.detail}</div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Raw Config And Debug" icon={<Terminal className="h-4 w-4 text-slate-300" />}>
            <pre className="max-h-72 overflow-auto rounded border border-slate-800 bg-black p-3 text-xs text-emerald-200">
              {displaySnapshot.rawConfig}
            </pre>
          </Panel>
        </section>
      </main>
    </div>
  )
}

export default App
