type WebSocketCallbacks = {
  onOpen?: (event: Event) => void;
  onMessage?: (event: MessageEvent) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
};

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WebSocketCallbacks;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private shouldReconnect = true;

  constructor(url: string, callbacks: WebSocketCallbacks = {}) {
    this.url = url;
    this.callbacks = callbacks;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log("WebSocket already connected");
      return;
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = (event) => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
      this.callbacks.onOpen?.(event);
    };

    this.ws.onmessage = (event) => {
      this.callbacks.onMessage?.(event);
    };

    this.ws.onerror = (event) => {
      console.error("WebSocket error:", event);
      this.callbacks.onError?.(event);
    };

    this.ws.onclose = (event) => {
      console.log("WebSocket closed");
      this.callbacks.onClose?.(event);
      this.ws = null;

      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    const backoffDelay = Math.min(
      this.maxReconnectDelay,
      1000 * Math.pow(2, this.reconnectAttempts)
    );

    this.reconnectAttempts += 1;

    console.log(
      `Scheduling reconnect attempt ${this.reconnectAttempts} in ${backoffDelay}ms`
    );

    this.reconnectTimeout = setTimeout(() => {
      console.log(`Reconnecting (attempt ${this.reconnectAttempts})...`);
      this.connect();
    }, backoffDelay);
  }

  send(data: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not connected");
      return;
    }

    const message = typeof data === "string" ? data : JSON.stringify(data);
    this.ws.send(message);
  }

  disconnect(): void {
    this.shouldReconnect = false;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export function createWebSocket(
  url: string,
  callbacks: WebSocketCallbacks = {}
): WebSocketClient {
  const client = new WebSocketClient(url, callbacks);
  client.connect();
  return client;
}
