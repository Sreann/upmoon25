import type { MissionControlSnapshot } from './types'

export type DemoScenario = 'nominal' | 'degraded' | 'offline'

export function createMockSnapshot(scenario: DemoScenario = 'degraded'): MissionControlSnapshot {
  const offline = scenario === 'offline'
  const degraded = scenario === 'degraded'
  const trends = Array.from({ length: 12 }, (_, index) => ({
    label: `${index * 10}s`,
    cpu: offline ? 0 : Math.round(28 + Math.sin(index / 2) * 8 + (degraded ? 4 : 0)),
    temp: offline ? 0 : Math.round(53 + Math.cos(index / 3) * 5),
    battery: offline ? 0 : Number((24.8 - index * 0.02).toFixed(1)),
    odomVelocity: offline ? 0 : Number((0.14 + Math.sin(index / 2) * 0.04).toFixed(2)),
    commandVelocity: offline ? 0 : degraded ? 0 : Number((0.16 + Math.cos(index / 2) * 0.03).toFixed(2)),
  }))

  return {
    mission: {
      connected: !offline,
      armed: false,
      estop: false,
      mode: offline ? 'Manual' : degraded ? 'Assisted' : 'Auto',
      state: offline ? 'IDLE' : degraded ? 'WAIT_FOR_ZONE_MARKS' : 'NAV_TO_DIG',
      target: offline ? 'No robot connection' : degraded ? 'Dump zone pending' : 'Dig zone',
      heartbeatMs: offline ? null : degraded ? 86 : 42,
      confidence: offline ? 0 : degraded ? 72 : 91,
      cycle: offline ? 0 : degraded ? 0 : 2,
      payload: offline ? 'unknown' : degraded ? 'empty' : 'loaded',
      stopReason: offline
        ? 'Robot bridge is offline. Motion controls must remain disabled.'
        : degraded
          ? 'Waiting for operator-marked dig and dump zones'
          : 'Driving short segment toward marked dig zone',
      lastDecision: offline
        ? 'No live telemetry available'
        : degraded
          ? 'Depth grid healthy; localization source not selected'
          : 'Local corridor clear; proceeding at limited speed',
      nextTransition: offline
        ? 'Reconnect bridge'
        : degraded
          ? 'Mark zones -> NAV_TO_DIG'
          : 'Reach dig tolerance -> DIG',
    },
    metrics: [
      { label: 'Linear Vel', value: offline ? '--' : degraded ? '0.00 m/s' : '0.18 m/s', detail: offline ? 'no cmd topic' : 'cmd/velocity', status: offline ? 'bad' : 'idle' },
      { label: 'Pose', value: offline ? '--' : degraded ? '0.0, 0.0' : '2.1, -0.4', detail: degraded ? 'odom unknown' : 'odom', status: degraded ? 'warn' : offline ? 'bad' : 'ok' },
      { label: 'Battery', value: offline ? '--' : '24.7 V', detail: offline ? 'no telemetry' : 'demo', status: offline ? 'bad' : 'ok' },
      { label: 'Latency', value: offline ? '--' : degraded ? '18 ms' : '12 ms', detail: 'dashboard bridge', status: offline ? 'bad' : 'ok' },
      { label: 'Point Cloud', value: offline ? '--' : degraded ? '18.4k pts' : '42.8k pts', detail: degraded ? 'awaiting hardware check' : 'live depth', status: degraded ? 'warn' : offline ? 'bad' : 'ok' },
      { label: 'Terrain Age', value: offline ? '--' : degraded ? '0.2 s' : '0.1 s', detail: degraded ? 'mock local grid' : 'local grid', status: offline ? 'bad' : 'ok' },
    ],
    topics: [
      { topic: '/camera/rgb/image_compressed', status: offline ? 'missing' : 'live', age: offline ? '--' : '44 ms', rate: offline ? '--' : '29.8 Hz', note: 'front RGB', safetyCritical: false },
      { topic: '/camera/rear/image_compressed', status: offline ? 'missing' : degraded ? 'connecting' : 'live', age: degraded || offline ? '--' : '51 ms', rate: degraded || offline ? '--' : '29.1 Hz', note: 'rear RGB', safetyCritical: false },
      { topic: '/camera/depth/points', status: offline ? 'missing' : degraded ? 'missing' : 'live', age: degraded || offline ? '--' : '80 ms', rate: degraded || offline ? '--' : '12.5 Hz', note: degraded ? 'not confirmed on hardware' : 'depth grid source', safetyCritical: true },
      { topic: '/odom', status: offline ? 'missing' : degraded ? 'stale' : 'live', age: offline ? '--' : degraded ? '3.8 s' : '36 ms', rate: offline ? '--' : degraded ? '0.0 Hz' : '30 Hz', note: 'localization source', safetyCritical: true },
      { topic: '/tf', status: offline ? 'missing' : degraded ? 'unknown' : 'live', age: offline ? '--' : degraded ? '--' : '40 ms', rate: offline ? '--' : degraded ? '--' : '25 Hz', note: 'frame transforms', safetyCritical: true },
      { topic: 'cmd/velocity', status: offline ? 'missing' : 'live', age: offline ? '--' : 'idle', rate: offline ? '--' : 'on command', note: 'watchdog required', safetyCritical: true },
    ],
    cameras: [
      { id: 'front', name: 'Front D435 RGB', topic: '/camera/rgb/image_compressed', status: offline ? 'missing' : 'live', fps: offline ? '--' : '30', resolution: '640x480' },
      { id: 'rear', name: 'Rear D435 RGB', topic: '/camera/rear/image_compressed', status: offline ? 'missing' : degraded ? 'connecting' : 'live', fps: degraded || offline ? '--' : '30', resolution: '640x480' },
    ],
    hardware: [
      { category: 'Vision', name: 'Front D435 RGB', status: offline ? 'NO DEVICE' : 'CONNECTED', detail: '018322071465', severity: offline ? 'bad' : 'ok' },
      { category: 'Vision', name: 'Rear D435 RGB', status: offline ? 'NO DEVICE' : degraded ? 'CONNECTING' : 'CONNECTED', detail: '018322071045', severity: degraded ? 'warn' : offline ? 'bad' : 'ok' },
      { category: 'Depth', name: '/camera/depth/points', status: degraded ? 'UNKNOWN' : offline ? 'NO TOPIC' : 'LIVE', detail: 'field audit required', severity: degraded ? 'warn' : offline ? 'bad' : 'ok' },
      { category: 'Actuation', name: 'Left Sabertooth', status: offline ? 'UNKNOWN' : 'CONNECTED', detail: '/dev/ttyACM0', severity: offline ? 'warn' : 'ok' },
      { category: 'Actuation', name: 'Right Sabertooth', status: offline ? 'UNKNOWN' : 'CONNECTED', detail: '/dev/ttyACM1', severity: offline ? 'warn' : 'ok' },
      { category: 'MCU', name: 'Arduino', status: offline ? 'UNKNOWN' : 'CONNECTED', detail: '/dev/ttyACM2', severity: offline ? 'warn' : 'ok' },
      { category: 'Sensors', name: 'Wheel Encoders', status: 'BAD DATA', detail: 'values do not make sense', severity: 'bad' },
    ],
    zones: [
      { id: 'start', label: 'Start zone', status: offline ? 'unknown' : 'operator_marked', detail: offline ? 'not marked' : 'ready' },
      { id: 'dig', label: 'Dig zone', status: 'unknown', detail: 'not marked' },
      { id: 'dump', label: 'Dump zone', status: degraded ? 'unknown' : offline ? 'unknown' : 'robot_detected', detail: degraded || offline ? 'not marked' : 'flag candidate' },
      { id: 'no_go', label: 'No-go region', status: 'unknown', detail: 'optional' },
    ],
    zoneMarking: offline
      ? { poseFrame: 'odom', odomTopic: '/odom', odomStatus: 'missing', odomAge: '--', x: 0, y: 0, yawDeg: null }
      : degraded
        ? { poseFrame: 'odom', odomTopic: '/odom', odomStatus: 'stale', odomAge: '3.8 s', x: 0, y: 0, yawDeg: 0 }
        : { poseFrame: 'odom', odomTopic: '/odom', odomStatus: 'live', odomAge: '36 ms', x: 2.1, y: -0.4, yawDeg: 118.4 },
    logs: [
      { ts: '00:00:01', level: offline ? 'error' : 'info', message: offline ? '[bridge] No robot bridge connection.' : '[mission] Waiting for marked dig and dump zones.' },
      { ts: '00:00:02', level: 'warn', message: '[safety] Drive commands require hold heartbeat.' },
      { ts: '00:00:03', level: degraded ? 'warn' : 'info', message: degraded ? '[localization] No trusted pose source selected.' : '[terrain] Local corridor clear.' },
      { ts: '00:00:04', level: degraded ? 'warn' : 'info', message: degraded ? '[depth] /camera/depth/points not confirmed.' : '[depth] Local terrain grid updated.' },
    ],
    trends,
    sensors: {
      irLeft: offline ? null : degraded ? 420 : 386,
      irRight: offline ? null : degraded ? 470 : 412,
      encoderLeft: offline ? null : degraded ? 118234 : 582,
      encoderRight: offline ? null : degraded ? -94211 : 579,
    },
    pid: {
      kp: 1.0,
      ki: 0.0,
      kd: 0.1,
    },
    audit: [
      { label: 'Emergency stop tested today', status: offline ? 'warn' : 'ok', detail: offline ? 'not connected' : 'operator confirms before field run' },
      { label: 'Manual stop command', status: offline ? 'bad' : 'ok', detail: offline ? 'bridge offline' : 'available through command API' },
      { label: 'Front/rear cameras', status: degraded ? 'warn' : offline ? 'bad' : 'ok', detail: degraded ? 'rear stream connecting' : offline ? 'no stream' : 'both live' },
      { label: 'Depth point cloud', status: degraded ? 'bad' : offline ? 'bad' : 'ok', detail: degraded ? 'not confirmed' : offline ? 'no topic' : 'live topic' },
      { label: 'Localization source', status: degraded ? 'warn' : offline ? 'bad' : 'ok', detail: degraded ? '/odom unknown' : offline ? 'no odom' : '/odom live' },
      { label: 'Dig/dump controls', status: offline ? 'bad' : 'ok', detail: offline ? 'disabled' : 'mock command path ready' },
    ],
    terrainGrid: (() => {
      const gw = 30
      const gh = 30
      const cells = Array.from({ length: gw * gh }, (_, index) => {
        const x = index % gw
        const y = Math.floor(index / gw)
        const x12 = Math.min(11, Math.floor((x * 12) / gw))
        const y12 = Math.min(11, Math.floor((y * 12) / gh))
        if ((x12 === 5 || x12 === 6) && y12 > 7) return 2
        if ((x12 > 7 && y12 < 4) || (x12 === 2 && y12 === 5) || (x12 === 3 && y12 === 5)) return 100
        if ((x12 < 3 && y12 < 3) || (x12 > 9 && y12 > 8)) return -1
        if (x12 === 7 && y12 === 6) return 60
        return 0
      })
      const obstacleCells = cells.filter((c) => c >= 90).length
      const cautionCells = cells.filter((c) => c > 0 && c < 90).length
      const unknownCells = cells.filter((c) => c < 0).length
      return {
        width: gw,
        height: gh,
        resolution: 0.1,
        frameId: 'base_link',
        ageMs: offline ? null : degraded ? 420 : 95,
        status: offline ? 'missing' : degraded ? 'stale' : 'live',
        cells,
        obstacleCells: offline ? 0 : obstacleCells,
        cautionCells: offline ? 0 : cautionCells,
        unknownCells: offline ? gw * gh : unknownCells,
        note: offline ? 'no terrain grid' : degraded ? 'mock stale grid' : 'mock local grid (30×30 @ 10 cm, matches standard preset footprint)',
      }
    })(),
    rawConfig: `# dashboard hardware summary
[vision.rgb_camera]
topic = "/camera/rgb/image_compressed"
status = "${offline ? 'missing' : 'connected'}"

[vision.rear_camera]
topic = "/camera/rear/image_compressed"
status = "${degraded ? 'connecting' : offline ? 'missing' : 'connected'}"

[depth]
topic = "/camera/depth/points"
status = "${degraded || offline ? 'unconfirmed' : 'live'}"

[safety]
drive_watchdog = true
browser_is_not_safety_layer = true`,
  }
}
