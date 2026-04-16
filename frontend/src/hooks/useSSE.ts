/**
 * useSSE — Server-Sent Events hook for DropSafe demo simulation.
 * Connects to an SSE endpoint, accumulates streamed events into state.
 */

import { useEffect, useRef, useState } from "react";

// Type definitions
export interface SSEEvent {
  step: number | "complete" | "error";
  total?: number;
  message: string;
  status: "success" | "failure" | "processing" | "warning" | "info" |
          "complete" | "review" | "fraud" | "blocked" | "fraud_blocked" |
          "cluster_blocked" | "error";
  timestamp?: string;
  detail?: string;
  payout_amount?: number;
  fraud_score?: number;
  scenario?: string;
  workers_blocked?: number;
  funds_protected?: number;
  error?: string;
}

interface UseSSEResult {
  events: SSEEvent[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  reset: () => void;
  start: (url: string, body: object) => void;
}

// Hook implementation
export function useSSE(): UseSSEResult {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setEvents([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
  };

  const start = async (url: string, body: object) => {
    reset();
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event: SSEEvent = JSON.parse(line.slice(6));
              setEvents((prev) => [...prev, event]);
              if (event.step === "complete" || event.step === "error") {
                setIsComplete(true);
                setIsStreaming(false);
              }
            } catch {
              // Skip malformed event
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message || "Connection failed");
      }
    } finally {
      setIsStreaming(false);
    }
  };

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return { events, isStreaming, isComplete, error, reset, start };
}
