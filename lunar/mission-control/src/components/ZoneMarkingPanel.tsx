import { clsx } from 'clsx'
import type { FieldZone, MissionControlSnapshot } from '../bridge/types'

const ZONE_ACCENT: Record<FieldZone['id'], string> = {
  start: 'border-l-emerald-500',
  dig: 'border-l-amber-500',
  dump: 'border-l-orange-500',
  no_go: 'border-l-red-500',
}

const ZONE_PREPARE_BTN: Record<FieldZone['id'], { idle: string; armed: string }> = {
  start: {
    idle: 'border-emerald-600/55 bg-emerald-950/55 text-emerald-100 hover:bg-emerald-900/55',
    armed: 'border-emerald-400 bg-emerald-500/30 text-emerald-50 ring-1 ring-emerald-400/45',
  },
  dig: {
    idle: 'border-amber-600/55 bg-amber-950/45 text-amber-100 hover:bg-amber-900/45',
    armed: 'border-amber-400 bg-amber-500/30 text-amber-50 ring-1 ring-amber-400/45',
  },
  dump: {
    idle: 'border-orange-600/55 bg-orange-950/45 text-orange-100 hover:bg-orange-900/45',
    armed: 'border-orange-400 bg-orange-500/30 text-orange-50 ring-1 ring-orange-400/45',
  },
  no_go: {
    idle: 'border-red-600/55 bg-red-950/50 text-red-100 hover:bg-red-900/50',
    armed: 'border-red-400 bg-red-500/25 text-red-50 ring-1 ring-red-400/45',
  },
}

export function ZoneMarkingPanel({
  snapshot,
  armedZone,
  onArm,
  canArm,
}: {
  snapshot: MissionControlSnapshot
  armedZone: FieldZone['id'] | null
  onArm: (zone: FieldZone['id'] | null) => void
  canArm: boolean
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {snapshot.zones.map((zone) => {
        const accent = ZONE_ACCENT[zone.id]
        const btn = ZONE_PREPARE_BTN[zone.id]
        const isArmed = armedZone === zone.id
        return (
          <div
            key={zone.id}
            className={clsx(
              'flex items-start justify-between gap-2 rounded-md border-y border-r border-slate-800 bg-slate-900/90 py-2 pl-2.5 pr-3',
              'border-l-4',
              accent,
            )}
          >
            <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug text-slate-100">{zone.label}</span>
            <button
              type="button"
              disabled={!canArm}
              onClick={() => onArm(isArmed ? null : zone.id)}
              className={clsx(
                'shrink-0 self-center rounded border px-2 py-1 text-xs font-semibold transition',
                isArmed ? btn.armed : btn.idle,
                !canArm && 'cursor-not-allowed opacity-40',
              )}
            >
              Prepare mark
            </button>
          </div>
        )
      })}
    </div>
  )
}
