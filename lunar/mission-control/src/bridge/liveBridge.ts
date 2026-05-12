import type { CommandResult, MissionControlSnapshot, RobotCommand } from './types'

type LiveBridgeOptions = {
  url: string
  onSnapshot: (snapshot: MissionControlSnapshot) => void
  onStatus: (status: LiveBridgeStatus) => void
}

export type LiveBridgeStatus = {
  connected: boolean
  connecting: boolean
  lastError: string | null
  lastMessageAt: number | null
}

type WireMessage =
  | { kind: 'snapshot'; snapshot: MissionControlSnapshot }
  | { kind: 'command_result'; requestId: string; result: CommandResult }
  | { kind: 'error'; message: string }

export class LiveRobotBridgeClient {
  private url: string
  private onSnapshot: (snapshot: MissionControlSnapshot) => void
  private onStatus: (status: LiveBridgeStatus) => void
  private socket: WebSocket | null = null
  private reconnectTimer: number | null = null
  private pending = new Map<string, (result: CommandResult) => void>()
  private status: LiveBridgeStatus = {
    connected: false,
    connecting: false,
    lastError: null,
    lastMessageAt: null,
  }

  constructor(options: LiveBridgeOptions) {
    this.url = options.url
    this.onSnapshot = options.onSnapshot
    this.onStatus = options.onStatus
  }

  connect() {
    if (this.socket || this.status.connecting) return

    this.setStatus({ connecting: true, lastError: null })
    const socket = new WebSocket(this.url)
    this.socket = socket

    socket.onopen = () => {
      this.setStatus({ connected: true, connecting: false, lastError: null })
    }

    socket.onmessage = (event) => {
      this.setStatus({ lastMessageAt: Date.now() })
      this.handleMessage(event.data)
    }

    socket.onerror = () => {
      this.setStatus({ lastError: 'WebSocket error' })
    }

    socket.onclose = () => {
      this.socket = null
      this.failPending('Bridge disconnected before command acknowledgement.')
      this.setStatus({ connected: false, connecting: false })
      this.scheduleReconnect()
    }
  }

  disconnect() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.socket?.close()
    this.socket = null
    this.failPending('Bridge disconnected.')
    this.setStatus({ connected: false, connecting: false })
  }

  sendCommand(command: RobotCommand): Promise<CommandResult> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return Promise.resolve({
        accepted: false,
        message: 'Live bridge is not connected.',
      })
    }

    const requestId = crypto.randomUUID()
    this.socket.send(JSON.stringify({ kind: 'command', requestId, command }))

    return new Promise((resolve) => {
      this.pending.set(requestId, resolve)
      window.setTimeout(() => {
        const pending = this.pending.get(requestId)
        if (!pending) return
        this.pending.delete(requestId)
        pending({
          accepted: false,
          message: 'Command acknowledgement timed out.',
          commandId: requestId,
        })
      }, 2000)
    })
  }

  private handleMessage(data: unknown) {
    let message: WireMessage
    try {
      message = JSON.parse(String(data)) as WireMessage
    } catch {
      this.setStatus({ lastError: 'Invalid bridge JSON message' })
      return
    }

    if (message.kind === 'snapshot') {
      this.onSnapshot(message.snapshot)
      return
    }

    if (message.kind === 'command_result') {
      const resolve = this.pending.get(message.requestId)
      if (!resolve) return
      this.pending.delete(message.requestId)
      resolve(message.result)
      return
    }

    if (message.kind === 'error') {
      this.setStatus({ lastError: message.message })
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== null) return
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, 1000)
  }

  private failPending(message: string) {
    for (const [requestId, resolve] of this.pending.entries()) {
      resolve({ accepted: false, message, commandId: requestId })
    }
    this.pending.clear()
  }

  private setStatus(next: Partial<LiveBridgeStatus>) {
    this.status = { ...this.status, ...next }
    this.onStatus(this.status)
  }
}
