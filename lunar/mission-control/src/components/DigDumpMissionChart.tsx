import { clsx } from 'clsx'
import type { MissionState } from '../bridge/types'

/** Ordered mission states for dig/dump cycle (loops RETURN_TO_DIG → IDLE). */
const MAIN_FLOW: MissionState[] = [
  'IDLE',
  'PERCEPTION_FAULT',
  'AWAIT_MARK_DIG',
  'AWAIT_MARK_DUMP',
  'NAV_READY',
  'NAV_ACTIVE',
  'DISCOVER_DUMP_ZONE',
  'NAV_TO_DIG',
  'DIG',
  'NAV_TO_DUMP',
  'DUMP',
  'RETURN_TO_DIG',
]

const BRANCH_STATES: MissionState[] = ['RECOVERY', 'PAUSED', 'ABORTED', 'ESTOP']

const NODE_LABEL: Record<MissionState, string> = {
  IDLE: 'IDLE',
  HEALTH_CHECK: 'HEALTH',
  WAIT_FOR_ZONE_MARKS: 'WAIT ZN',
  READY: 'READY',
  PERCEPTION_FAULT: 'PERC',
  PERCEPTION_STALE: 'P-STALE',
  LOCALIZATION_LOST: 'NO ODOM',
  TERRAIN_FAULT: 'GRID',
  TERRAIN_STALE: 'G-STALE',
  AWAIT_MARK_DIG: 'MARK DG',
  AWAIT_MARK_DUMP: 'MARK DP',
  NAV_READY: 'NAV RDY',
  NAV_ACTIVE: 'NAV ON',
  DISCOVER_DUMP_ZONE: 'FIND DP',
  NAV_TO_DIG: '→ DIG',
  DIG: 'DIG',
  NAV_TO_DUMP: '→ DUMP',
  DUMP: 'DUMP',
  RETURN_TO_DIG: 'RET DIG',
  RECOVERY: 'REC',
  PAUSED: 'PAUSE',
  ABORTED: 'ABORT',
  ESTOP: 'E-STOP',
}

function polar(cx: number, cy: number, r: number, angleRad: number) {
  return { x: cx + r * Math.cos(angleRad), y: cy + r * Math.sin(angleRad) }
}

function edgeSegment(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  nodeR: number,
): { x1: number; y1: number; x2: number; y2: number } {
  const dx = bx - ax
  const dy = by - ay
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  return {
    x1: ax + ux * nodeR,
    y1: ay + uy * nodeR,
    x2: bx - ux * nodeR,
    y2: by - uy * nodeR,
  }
}

function nodeFillStroke(isCurrent: boolean, isPast: boolean): { fill: string; stroke: string; strokeW: number } {
  if (isCurrent) {
    return { fill: 'rgba(245, 158, 11, 0.22)', stroke: '#fbbf24', strokeW: 2.25 }
  }
  if (isPast) {
    return { fill: 'rgba(6, 78, 59, 0.45)', stroke: 'rgba(52, 211, 153, 0.55)', strokeW: 1.5 }
  }
  return { fill: 'rgba(15, 23, 42, 0.92)', stroke: '#475569', strokeW: 1.25 }
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
            ? 'border-amber-400 bg-amber-500/25 text-amber-50 shadow-[0_0_0_2px_rgba(251,191,36,0.45)]'
            : 'border-slate-700 bg-slate-900/80 text-slate-500',
      )}
    >
      {id.replace(/_/g, ' ')}
    </div>
  )
}

const VB = 560
const CX = VB / 2
const CY = VB / 2
const R = 198
const NODE_R = 30

/** Circular dig/dump mission architecture (supervisor states; dig/nav nodes run subsets). */
export function DigDumpMissionChart({ current }: { current: MissionState }) {
  const n = MAIN_FLOW.length
  const mainIdx = MAIN_FLOW.indexOf(current)
  const unknown = !MAIN_FLOW.includes(current) && !BRANCH_STATES.includes(current)

  const angles = MAIN_FLOW.map((_, i) => -Math.PI / 2 + (2 * Math.PI * i) / n)
  const pos = angles.map((a) => polar(CX, CY, R, a))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
        <span>
          Mission state: <span className="font-mono text-amber-200">{current}</span>
          {unknown ? <span className="ml-2 text-amber-500">(not in diagram set — still shown)</span> : null}
        </span>
        <span className="hidden sm:inline">Dig / dump loop · clockwise</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/50 p-2 sm:p-4">
        <svg
          role="img"
          aria-label="Dig and dump mission state machine as a circular loop"
          viewBox={`0 0 ${VB} ${VB}`}
          className="mx-auto h-auto w-full max-w-[min(100%,520px)]"
          preserveAspectRatio="xMidYMid meet"
        >
          <title>Dig dump mission — main path is a closed loop</title>
          <defs>
            <marker
              id="ddm-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L8,4 L0,8 z" fill="#64748b" />
            </marker>
            <marker
              id="ddm-arrow-active"
              markerWidth="9"
              markerHeight="9"
              refX="8"
              refY="4.5"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L9,4.5 L0,9 z" fill="#fbbf24" />
            </marker>
            <filter id="ddm-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="1.2" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(51,65,85,0.35)" strokeWidth="1" strokeDasharray="4 6" />

          {MAIN_FLOW.map((_, i) => {
            const j = (i + 1) % n
            const { x1, y1, x2, y2 } = edgeSegment(pos[i].x, pos[i].y, pos[j].x, pos[j].y, NODE_R)
            const isActiveEdge = mainIdx === i
            return (
              <line
                key={`e-${MAIN_FLOW[i]}-${MAIN_FLOW[j]}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={isActiveEdge ? '#fbbf24' : '#475569'}
                strokeWidth={isActiveEdge ? 2 : 1.25}
                strokeOpacity={isActiveEdge ? 0.95 : 0.75}
                markerEnd={isActiveEdge ? 'url(#ddm-arrow-active)' : 'url(#ddm-arrow)'}
                filter={isActiveEdge ? 'url(#ddm-glow)' : undefined}
              />
            )
          })}

          {(() => {
            const last = n - 1
            const { x1, y1, x2, y2 } = edgeSegment(pos[last].x, pos[last].y, pos[0].x, pos[0].y, NODE_R)
            const mx = (x1 + x2) / 2
            const my = (y1 + y2) / 2
            const vx = CX - mx
            const vy = CY - my
            const vlen = Math.hypot(vx, vy) || 1
            const tx = mx + (vx / vlen) * 22
            const ty = my + (vy / vlen) * 22
            return (
              <text
                x={tx}
                y={ty}
                textAnchor="middle"
                dominantBaseline="middle"
                className="fill-slate-500"
                style={{ fontSize: 9, fontFamily: 'ui-monospace, monospace' }}
              >
                loop
              </text>
            )
          })()}

          {MAIN_FLOW.map((id, i) => {
            const { x, y } = pos[i]
            const selfIdx = i
            const isCurrent = current === id
            const isPast = selfIdx !== -1 && mainIdx !== -1 && selfIdx < mainIdx
            const { fill, stroke, strokeW } = nodeFillStroke(isCurrent, isPast)
            return (
              <g key={id} transform={`translate(${x}, ${y})`}>
                <circle r={NODE_R} fill={fill} stroke={stroke} strokeWidth={strokeW} />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  className={clsx(
                    'pointer-events-none select-none font-mono font-semibold',
                    isCurrent ? 'fill-amber-50' : isPast ? 'fill-emerald-100/90' : 'fill-slate-500',
                  )}
                  style={{ fontSize: 10 }}
                >
                  {NODE_LABEL[id]}
                </text>
                <title>{id}</title>
              </g>
            )
          })}

          <text
            x={CX}
            y={CY + 4}
            textAnchor="middle"
            className="fill-slate-600"
            style={{ fontSize: 10, fontFamily: 'ui-monospace, monospace' }}
          >
            dig / dump cycle
          </text>
        </svg>
      </div>

      <div className="border-t border-slate-800 pt-3">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Interrupt / hold</div>
        <div role="list" aria-label="Mission branch states" className="flex flex-wrap items-center gap-2">
          {BRANCH_STATES.map((id) => (
            <BranchPill key={id} id={id} current={current} />
          ))}
        </div>
      </div>

      <p className="text-[11px] leading-relaxed text-slate-500">
        This chart is the <span className="text-slate-300">target excavation mission</span> (idle → health → zones → navigate → dig/dump → return). Wire it in
        mission_exec when autonomous dig/dump is implemented; <span className="text-slate-300">Nav autonomy</span> (beside this panel) tracks readiness from /autonomy/state.
      </p>
    </div>
  )
}
