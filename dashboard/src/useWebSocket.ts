import { useEffect, useReducer, useRef } from "react";
import {
  createInitialDashboardStore,
  dashboardStoreReducer,
} from "./store";

export function useWebSocket(url: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const [store, dispatch] = useReducer(
    dashboardStoreReducer,
    undefined,
    createInitialDashboardStore,
  );

  useEffect(() => {
    dispatch({ type: "status", status: "connecting" });
    let stopped = false;
    let attempt = 0;
    let timer: number | undefined;
    const pruneTimer = window.setInterval(() => {
      dispatch({ type: "prune", now: Date.now() });
    }, 1000);

    const connect = () => {
      if (stopped) return;
      const socket = new WebSocket(url);
      socketRef.current = socket;
      socket.onopen = () => {
        attempt = 0;
        dispatch({ type: "status", status: "open" });
      };
      socket.onmessage = (event) => {
        try {
          const value: unknown = JSON.parse(event.data);
          dispatch({ type: "message", value, receivedAt: Date.now() });
        } catch {
          dispatch({ type: "dropped-message" });
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        dispatch({ type: "reconnecting" });
        const delay = Math.min(1000 * 2 ** attempt, 30000);
        attempt += 1;
        timer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      stopped = true;
      dispatch({ type: "status", status: "closed" });
      if (timer !== undefined) window.clearTimeout(timer);
      window.clearInterval(pruneTimer);
      socketRef.current?.close();
    };
  }, [url]);

  return { status: store.status, store };
}
