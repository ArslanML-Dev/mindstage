"use client";
import { useEffect, useRef, useState } from "react";
import { WS_URL } from "./api";

export type LiveMessage =
  | { type: "scene"; index: number }
  | { type: "presence"; students: string[] }
  | { type: "stats"; scene: number; question: number; counts: number[] }
  | { type: "answer_result"; scene: number; question: number; correct: boolean }
  | { type: "doubt"; student: string; question: string; answer: string };

/** Keeps a WebSocket to the class room open (reconnecting if it drops) and hands every message to onMessage. */
export function useLive(code: string, query: string, onMessage: (m: LiveMessage) => void, enabled = true) {
  const ws = useRef<WebSocket | null>(null);
  const handler = useRef(onMessage);
  handler.current = onMessage;
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let retry: ReturnType<typeof setTimeout>;
    const connect = () => {
      const sock = new WebSocket(`${WS_URL}/ws/${code}?${query}`);
      ws.current = sock;
      sock.onopen = () => setConnected(true);
      sock.onmessage = (e) => handler.current(JSON.parse(e.data));
      sock.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(retry);
      ws.current?.close();
    };
  }, [code, query, enabled]);

  const send = (msg: object) => ws.current?.readyState === WebSocket.OPEN && ws.current.send(JSON.stringify(msg));
  return { connected, send };
}
