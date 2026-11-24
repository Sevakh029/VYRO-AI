import { useEffect, useRef, useState } from "react";
import {
  messageKey,
  parseTopicMessage,
  pruneStaleVehicleStates,
  type TopicMessageStore,
} from "./types";

export function useWebSocket(url: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Connecting");
  const [messages, setMessages] = useState<TopicMessageStore>({});

  useEffect(() => {
    let stopped = false;
    let attempt = 0;
    let timer: number | undefined;
    const pruneTimer = window.setInterval(() => {
      setMessages((current) => pruneStaleVehicleStates(current));
    }, 1000);

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
          const value: unknown = JSON.parse(event.data);
          const message = parseTopicMessage(value);
          if (!message) {
            setStatus("Invalid message");
            return;
          }
          const key = messageKey(message);
          setMessages((current) => ({
            ...current,
            [message.topic]: {
              ...current[message.topic],
              [key]: message,
            },
          }));
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
      window.clearInterval(pruneTimer);
      socketRef.current?.close();
    };
  }, [url]);

  return { status, messages };
}
