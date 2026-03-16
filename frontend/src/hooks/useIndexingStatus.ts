import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api/client";
import type { WsEvent, ProjectStatus } from "../api/types";

export interface IndexingState {
  message: string;
  progress: number;
  status: ProjectStatus | null;
  connected: boolean;
}

export function useIndexingStatus(
  projectId: string,
  active: boolean
): IndexingState {
  const [state, setState] = useState<IndexingState>({
    message: "",
    progress: 0,
    status: null,
    connected: false,
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!active) return;

    const ws = new WebSocket(wsUrl(projectId));
    wsRef.current = ws;

    ws.onopen = () => setState((s) => ({ ...s, connected: true }));

    ws.onmessage = (evt) => {
      try {
        const event: WsEvent = JSON.parse(evt.data);
        setState((s) => ({
          ...s,
          message: event.message ?? s.message,
          progress: event.progress ?? s.progress,
          status: event.status ?? s.status,
        }));
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => setState((s) => ({ ...s, connected: false }));

    return () => { ws.close(); };
  }, [projectId, active]);

  return state;
}
