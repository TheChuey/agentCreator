/* Project Manager WebSocket session module */
let ws = null;
let wsConnected = false;
let reconnectTimeout = null;

const Session = {
  onEvent: null,
  onConnect: null,
  onDisconnect: null,

  connect() {
    if (ws && wsConnected) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/api/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsConnected = true;
      if (this.onConnect) this.onConnect();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (this.onEvent) this.onEvent(msg);
      } catch (e) {
        console.warn('Failed to parse WS message', e);
      }
    };

    ws.onclose = () => {
      wsConnected = false;
      if (this.onDisconnect) this.onDisconnect();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(() => this.connect(), 2000);
    };

    ws.onerror = (e) => {
      console.error('WebSocket error', e);
    };
  },

  send(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  },

  sendOpen(path) {
    this.send({ type: 'open', path });
  },

  sendDirty(dirty) {
    this.send({ type: 'dirty', dirty });
  },

  sendSessions() {
    this.send({ type: 'sessions' });
  }
};

export default Session;
