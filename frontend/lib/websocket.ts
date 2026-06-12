
import type { WSMessage, WSMessageType } from "./types";

type Listener = (data: unknown) => void;

class OpsPilotSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<WSMessageType | "*", Set<Listener>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[OpsPilot WS] connected");
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data as string);
          this.emit(msg.type, msg.data);
          this.emit("*", msg);
        } catch {
          // malformed frame, ignore
        }
      };

      this.ws.onclose = () => {
        console.log("[OpsPilot WS] disconnected");
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(() => this.connect(), 3000);
        }
      };

      this.ws.onerror = (e) => {
        console.error("[OpsPilot WS] error", e);
      };
    } catch (e) {
      console.error("[OpsPilot WS] failed to create socket", e);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  on(type: WSMessageType | "*", cb: Listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(cb);
    return () => this.off(type, cb);
  }

  off(type: WSMessageType | "*", cb: Listener) {
    this.listeners.get(type)?.delete(cb);
  }

  private emit(type: WSMessageType | "*", data: unknown) {
    this.listeners.get(type)?.forEach((cb) => cb(data));
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

const WS_URL =
  (typeof window !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) ||
  "ws://localhost:8000/ws";

export const socket = new OpsPilotSocket(WS_URL);

import { useEffect } from "react";

export function useWSEvent(
  type: WSMessageType | "*",
  handler: Listener,
  deps: unknown[] = []
) {
  useEffect(() => {
    const unsub = socket.on(type, handler);
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}