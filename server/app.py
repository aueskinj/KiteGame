"""HTTP + WebSocket server using only the standard library.

* GET /            -> static/index.html (and the other files in static/)
* GET /ws          -> upgrades to a WebSocket; one private game per connection

Each connection runs in its own thread. The thread owns a GameState, reads
input messages from the socket, and steps the simulation on a fixed 60 Hz
timestep (catching up if it falls behind, capped so a stall cannot spiral).
State goes back to the client at 30 Hz.
"""

import json
import os
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from game import config
from game.kite import Controls
from game.state import GameState
from . import websocket as ws

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
                 ".ico": "image/x-icon"}
MAX_CLIENTS = 64
SEND_EVERY = 2          # send a snapshot every N ticks (60 / 2 = 30 Hz)
MAX_CATCHUP = 5         # never run more than this many ticks in one go
IDLE_TIMEOUT = 120.0    # drop a client that sends nothing for this long

_slots = threading.BoundedSemaphore(MAX_CLIENTS)


def parse_input(msg, controls):
    """Apply a client message to `controls`. Returns 'restart', 'ok' or None (ignored)."""
    if not isinstance(msg, dict):
        return None
    kind = msg.get("type")
    if kind == "input":
        for name in ("left", "right", "up", "down"):
            v = msg.get(name)
            if isinstance(v, bool):
                setattr(controls, name, v)
        return "ok"
    if kind == "restart":
        return "restart"
    if kind == "ping":
        return "ok"
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "KiteGame/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    # --- routing ---------------------------------------------------------

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/ws":
            return self._websocket()
        if path == "/":
            path = "/index.html"
        self._static(path)

    def _static(self, path):
        name = os.path.normpath(path.lstrip("/"))
        full = os.path.join(STATIC_DIR, name)
        # normpath collapses "..", so this also rejects anything that escapes static/.
        if (name.startswith("..") or os.path.isabs(name) or not os.path.isfile(full)
                or os.path.commonpath([STATIC_DIR, os.path.abspath(full)]) != STATIC_DIR):
            body = b"Not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        with open(full, "rb") as f:
            body = f.read()
        ext = os.path.splitext(full)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # --- websocket -------------------------------------------------------

    def _websocket(self):
        h = self.headers
        key = h.get("Sec-WebSocket-Key")
        ok = (h.get("Upgrade", "").lower() == "websocket"
              and "upgrade" in h.get("Connection", "").lower()
              and key and h.get("Sec-WebSocket-Version") == "13")
        if not ok:
            self.send_error(400, "Expected a WebSocket upgrade")
            return
        # Refuse cross-site pages: the Origin's host must be the host we were asked for.
        origin = h.get("Origin")
        if origin and origin.split("://", 1)[-1] != h.get("Host", ""):
            self.send_error(403, "Cross-origin WebSocket refused")
            return
        if not _slots.acquire(blocking=False):
            self.send_error(503, "Server full")
            return
        try:
            self.close_connection = True
            self.wfile.write(ws.handshake_response(key))
            self.wfile.flush()
            Session(self.connection, seed=int(time.time() * 1000) & 0x7FFFFFFF).run()
        finally:
            _slots.release()


class Session:
    """One player's game, driven over one WebSocket."""

    def __init__(self, sock, seed):
        self.sock = sock
        self.parser = ws.FrameParser(require_mask=True)
        self.game = GameState(seed=seed)
        self.controls = Controls()
        self.alive = True
        self.last_heard = time.monotonic()

    def send_json(self, obj):
        self._send(ws.encode_frame(ws.OP_TEXT, json.dumps(obj, separators=(",", ":"))))

    def _send(self, data):
        try:
            self.sock.sendall(data)
        except OSError:
            self.alive = False

    def run(self):
        self.sock.setblocking(False)
        self.send_json({"type": "init", **self.game.static_info()})
        self.send_json({"type": "state", **self.game.snapshot()})
        next_tick = time.monotonic()
        tick = 0
        pending_events = []
        while self.alive:
            now = time.monotonic()
            # Run every tick that is due.
            ran = 0
            while next_tick <= now and ran < MAX_CATCHUP and self.alive:
                pending_events.extend(self.game.step(self.controls))
                next_tick += config.DT
                tick += 1
                ran += 1
                if tick % SEND_EVERY == 0:
                    snap = self.game.snapshot()
                    snap["events"] = pending_events
                    pending_events = []
                    self.send_json({"type": "state", **snap})
            if next_tick <= now:                     # fell far behind: drop the backlog
                next_tick = now + config.DT
            if now - self.last_heard > IDLE_TIMEOUT:
                break
            # Sleep until the next tick or until the client says something.
            wait = max(0.0, next_tick - time.monotonic())
            try:
                readable, _, _ = select.select([self.sock], [], [], wait)
            except (OSError, ValueError):
                break
            if readable:
                self._read()
        try:
            self.sock.sendall(ws.close_frame(1001))
        except OSError:
            pass

    def _read(self):
        try:
            data = self.sock.recv(4096)
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            self.alive = False
            return
        if not data:
            self.alive = False
            return
        self.last_heard = time.monotonic()
        try:
            messages = self.parser.feed(data)
        except ws.ProtocolError:
            self._send(ws.close_frame(1002))
            self.alive = False
            return
        for opcode, payload in messages:
            if opcode == ws.OP_CLOSE:
                self._send(ws.close_frame(1000))
                self.alive = False
            elif opcode == ws.OP_PING:
                self._send(ws.encode_frame(ws.OP_PONG, payload))
            elif opcode == ws.OP_TEXT:
                try:
                    msg = json.loads(payload.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if parse_input(msg, self.controls) == "restart" and self.game.phase == "game_over":
                    self.game.restart()
                    self.controls = Controls()


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    verbose = False

    def handle_error(self, request, client_address):
        pass  # dropped connections are normal for a game server


def make_server(host="127.0.0.1", port=5000):
    return QuietServer((host, port), Handler)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="KiteGame server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    srv = make_server(args.host, args.port)
    srv.verbose = args.verbose
    print("KiteGame running at http://%s:%d  (Ctrl+C to stop)" % (args.host, args.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
