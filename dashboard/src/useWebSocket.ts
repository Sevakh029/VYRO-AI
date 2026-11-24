import { useEffect, useRef, useState } from "react";

export function useWebSocket(url: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Connecting");
  const [messages, setMessages] = useState<Record<string, unknown>>({});

  useEffect(() => {
    let stopped = false;
    let attempt = 0;
    let timer: number | undefined;

    const connect = () => {
      if (stopped) return;
      const socket = new WebSocket(url);
      socketRef.current = socket;
      socket.onopen = () => {
        attempt = 0;
        setStatus("Live");
      };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as Record<string, unknown>;
          const topic = typeof message.topic === "string" ? message.topic : "broadcast";
          setMessages((current) => ({ ...current, [topic]: message }));
        } catch {
          setStatus("Invalid message");
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        setStatus("Disconnected");
        const delay = Math.min(1000 * 2 ** attempt, 30000);
        attempt += 1;
        timer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      stopped = true;
      if (timer) window.clearTimeout(timer);
      socketRef.current?.close();
    };
  }, [url]);

  return { status, messages };
}
