import { useEffect, useRef, useCallback } from 'react';

export interface AlertEvent {
  user_id: string;
  type: 'price_alert' | 'test';
  title: string;
  body: string;
  symbol: string;
  price: string;
  condition: string;
  timestamp: string;
}

interface UseAlertStreamOptions {
  onAlert: (event: AlertEvent) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Connects to the SSE ``/notifications/stream`` endpoint and invokes
 * ``onAlert`` for every alert that arrives.
 *
 * Automatically reconnects on disconnect with exponential backoff.
 */
export function useAlertStream({ onAlert }: UseAlertStreamOptions) {
  const onAlertRef = useRef(onAlert);
  onAlertRef.current = onAlert;

  const retryDelay = useRef(1000);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    let es: EventSource | null = null;
    let closed = false;

    function connect() {
      if (closed) return;

      const url = `${API_URL}/api/v1/notifications/stream?token=${encodeURIComponent(token!)}`;
      es = new EventSource(url);

      es.onopen = () => {
        retryDelay.current = 1000;
      };

      es.onmessage = (event) => {
        try {
          const data: AlertEvent = JSON.parse(event.data);
          onAlertRef.current(data);
        } catch {
          // heartbeat comments or bad JSON -- ignore
        }
      };

      es.onerror = () => {
        es?.close();
        if (!closed) {
          const delay = retryDelay.current;
          retryDelay.current = Math.min(delay * 2, 30000);
          setTimeout(connect, delay);
        }
      };
    }

    connect();

    return () => {
      closed = true;
      es?.close();
    };
  }, []);
}

let audioCtx: AudioContext | null = null;

/**
 * Play a short two-tone alert chime using the Web Audio API.
 * No external sound file needed.
 */
export function playAlertSound() {
  try {
    if (!audioCtx) {
      audioCtx = new AudioContext();
    }

    const now = audioCtx.currentTime;

    function tone(freq: number, start: number, duration: number) {
      const osc = audioCtx!.createOscillator();
      const gain = audioCtx!.createGain();

      osc.type = 'sine';
      osc.frequency.value = freq;

      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.3, start + 0.02);
      gain.gain.linearRampToValueAtTime(0, start + duration);

      osc.connect(gain);
      gain.connect(audioCtx!.destination);

      osc.start(start);
      osc.stop(start + duration);
    }

    // Two ascending tones: D5 → A5
    tone(587, now, 0.15);
    tone(880, now + 0.18, 0.25);
  } catch {
    // Web Audio API not available or blocked -- ignore
  }
}
