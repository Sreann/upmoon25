import { clsx } from 'clsx'
import type { MissionState } from '../bridge/types'

/** Ordered nav readiness states from `compute_shadow_tick` / `/autonomy/state`. */
const NAV_AUTONOMY_FLOW: MissionState[] = [
  'PERCEPTION_FAULT',
  'PERCEPTION_STALE',
  'LOCALIZATION_LOST',
  'TERRAIN_FAULT',
  'TERRAIN_STALE',
  'AWAIT_MARK_DIG',
  'AWAIT_MARK_DUMP',
  'NAV_READY',
  'NAV_ACTIVE',
]

const BRANCH: MissionState[] = ['RECOVERY', 'PAUSED', 'ABORTED', 'ESTOP']

const SHORT_LABEL: Record<MissionState, string> = {
  IDLE: 'IDLE',
  HEALTH_CHECK: 'HEALTH',
  WAIT_FOR_ZONE_MARKS: 'ZONES',
  READY: 'READY',
  PERCEPTION_FAULT: 'PERC',
  PERCEPTION_STALE: 'P-ST',
  LOCALIZATION_LOST: 'ODOM',
  TERRAIN_FAULT: 'GRID',
  TERRAIN_STALE: 'GR-ST',
  AWAIT_MARK_DIG: 'DIG',
  AWAIT_MARK_DUMP: 'DUMP',
  NAV_READY: 'N-RDY',
  NAV_ACTIVE: 'N-ACT',
  DISCOVER_DUMP_ZONE: 'FIND DP',
  NAV_TO_DIG: '→ DIG',
  DIG: 'DIG',
  NAV_TO_DUMP: '→ DP',
  DUMP: 'DUMP',
  RETURN_TO_DIG: 'RET',
  RECOVERY: 'REC',
  PAUSED: 'PAUSE',
  ABORTED: 'ABORT',
  ESTOP: 'E-STOP',
}

const MISSION_EXEC_STATES = new Set<MissionState>([
  'IDLE',
  'DISCOVER_DUMP_ZONE',
  'NAV_TO_DIG',
  'DIG',
  'NAV_TO_DUMP',
  'DUMP',
  'RETURN_TO_DIG',
])

function nodeStyle(isCurrent: boolean, isPast: boolean) {
  if (isCurrent) return { fill: 'rgba(56, 189, 248, 0.2)', stroke: '#38bdf8', sw: 2.25 }
  if (isPast) return { fill: 'rgba(6, 78, 59, 0.45)', stroke: 'rgba(52, 211, 153, 0.55)', sw: 1.5 }
  return { fill: 'rgba(15, 23, 42, 0.92)', stroke: '#475569', sw: 1.25 }
}

function BranchPill({ id, current }: { id: MissionState; current: MissionState }) {
  const isCurrent = current === id
  const isDanger = id === 'ESTOP' || id === 'ABORTED'
  return (
    <div
      role="listitem"
      aria-current={isCurrent ? 'step' : undefined}
      className={clsx(
        'rounded-md border px-2 py-1.5 text-center font-mono text-[10px] font-semibold sm:text-[11px]',
        isCurrent && isDanger
          ? 'border-red-400 bg-red-950/60 text-red-100 shadow-[0_0_0_2px_rgba(248,113,113,0.4)]'
          : isCurrent
            ? 'border-sky-400 bg-sky-500/20 text-sky-50 shadow-[0_0_0_2px_rgba(56,189,248,0.4)]'
            : 'border-slate-700 bg-slate-900/80 text-slate-500',
      )}
    >
      {id.replace(/_/g, ' ')}
    </div>
  )
}

const W = 920
const H = 200
const NODE_R = 19
const Y = 100
const MARGIN = 52

function pipelineXs(n: number): number[] {
  if (n <= 1) return [W / 2]
  const span = W - 2 * MARGIN
  return Array.from({ length: n }, (_, i) => MARGIN + (i * span) / (n - 1))
}

/** Readiness pipeline from `/autonomy/state` (published by `autonomy_supervisor` in the backend). */
export function NavAutonomyStateChart({ current }: { current: MissionState }) {
  const XS = pipelineXs(NAV_AUTONOMY_FLOW.length)
  const pipeIdx = NAV_AUTONOMY_FLOW.indexOf(current)
  const onBranch = BRANCH.includes(current)
  const missionOnly = MISSION_EXEC_STATES.has(current) && pipeIdx === -1 && !onBranch

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
        <span>
          State: <span className="font-mono text-sky-200">{current}</span>
        </span>
        <span className="hidden sm:inline">Nav autonomy readiness · /autonomy/state</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/50 p-2 sm:p-4">
        <svg
          role="img"
          aria-label="Nav autonomy readiness pipeline"
          viewBox={`0 0 ${W} ${H}`}
          className="mx-auto h-auto w-full max-w-[min(100%,920px)]"
          preserveAspectRatio="xMidYMid meet"
        >
          <title>Nav autonomy readiness pipeline</title>
          <defs>
            <marker id="nav-auto-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L7,3.5 L0,7 z" fill="#64748b" />
            </marker>
            <marker id="nav-auto-arrow-active" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L8,4 L0,8 z" fill="#38bdf8" />
            </marker>
          </defs>

          {NAV_AUTONOMY_FLOW.map((_, i) => {
            if (i >= NAV_AUTONOMY_FLOW.length - 1) return null
            const x1 = XS[i]! + NODE_R
            const x2 = XS[i + 1]! - NODE_R
            const active = pipeIdx === i
            return (
              <line
                key={`nav-auto-e-${i}`}
                x1={x1}
                y1={Y}
                x2={x2}
                y2={Y}
                stroke={active ? '#38bdf8' : '#475569'}
                strokeWidth={active ? 2 : 1.25}
                markerEnd={active ? 'url(#nav-auto-arrow-active)' : 'url(#nav-auto-arrow)'}
              />
            )
          })}

          {NAV_AUTONOMY_FLOW.map((id, i) => {
            const x = XS[i]!
            const isCurrent = current === id
            const isPast = pipeIdx !== -1 && i < pipeIdx
            const { fill, stroke, sw } = nodeStyle(isCurrent, isPast)
            return (
              <g key={id} transform={`translate(${x}, ${Y})`}>
                <circle r={NODE_R} fill={fill} stroke={stroke} strokeWidth={sw} />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  className={clsx(
                    'pointer-events-none select-none font-mono font-semibold',
                    isCurrent ? 'fill-sky-50' : isPast ? 'fill-emerald-100/90' : 'fill-slate-500',
                  )}
                  style={{ fontSize: 9 }}
                >
                  {SHORT_LABEL[id]}
                </text>
                <title>{id}</title>
              </g>
            )
          })}

          <text x={W / 2} y={28} textAnchor="middle" className="fill-slate-600" style={{ fontSize: 10, fontFamily: 'ui-monospace, monospace' }}>
            nav autonomy
          </text>
        </svg>
      </div>

      <div className="border-t border-slate-800 pt-3">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Interrupt / hold</div>
        <div role="list" aria-label="Nav autonomy branch states" className="flex flex-wrap items-center gap-2">
          {BRANCH.map((id) => (
            <BranchPill key={id} id={id} current={current} />
          ))}
        </div>
      </div>

      {missionOnly ? (
        <p className="text-[11px] leading-relaxed text-amber-200/90">
          <span className="font-mono">{current}</span> is a <span className="text-slate-200">mission chart</span> state; nav autonomy does not run that path yet. Use the dig/dump diagram for mission planning context.
        </p>
      ) : (
        <p className="text-[11px] leading-relaxed text-slate-500">
          <span className="font-mono text-slate-400">autonomy_supervisor</span> publishes this from perception, terrain, odom, and zone marks. At{' '}
          <span className="font-mono text-slate-400">NAV_READY</span>, set <span className="font-mono text-slate-400">/autonomy/navigation_active</span> to reach{' '}
          <span className="font-mono text-slate-400">NAV_ACTIVE</span> for short-segment twists.
        </p>
      )}
    </div>
  )
}
