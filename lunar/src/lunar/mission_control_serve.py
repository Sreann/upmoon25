"""Serve mission-control ``dist/`` and proxy bridge WebSockets on one HTTP port.

Used by ``lunar dashboard`` when pnpm is unavailable but ``dist/`` exists, so operators
only open :8501 and WebSockets use the same origin (no separate :8770 / :8767 in the browser).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado import gen
from tornado.websocket import websocket_connect


class _BridgeWebSocketProxy(tornado.websocket.WebSocketHandler):
    """Forward browser WebSocket to camera_ws or mission_bridge on localhost."""

    def initialize(self, upstream_port: int):
        self._upstream_port = int(upstream_port)
        self._upstream = None

    def check_origin(self, origin):
        return True

    @gen.coroutine
    def open(self, *args, **kwargs):
        path = self.request.path
        query = self.request.query
        uri = path if not query else f"{path}?{query}"
        target = f"ws://127.0.0.1:{self._upstream_port}{uri}"
        try:
            self._upstream = yield websocket_connect(target)
        except Exception as exc:
            self.close(1011, f"upstream connect failed: {exc}")
            return

        def on_upstream_message(msg):
            if self.ws_connection is None:
                return
            if isinstance(msg, bytes):
                self.write_message(msg, binary=True)
            else:
                self.write_message(msg)

        def on_upstream_close():
            if self.ws_connection is not None:
                self.close()

        self._upstream.on_message = on_upstream_message
        self._upstream.on_close = on_upstream_close

    def on_message(self, message):
        if self._upstream is None:
            return
        if isinstance(message, bytes):
            self._upstream.write_message(message, binary=True)
        else:
            self._upstream.write_message(message)

    def on_close(self):
        if self._upstream is not None:
            self._upstream.close()
            self._upstream = None


class _HealthProxyHandler(tornado.web.RequestHandler):
    def initialize(self, upstream_port: int):
        self._upstream_port = int(upstream_port)

    async def get(self):
        import urllib.request

        url = f"http://127.0.0.1:{self._upstream_port}/healthz"
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                body = resp.read()
                self.set_header("Content-Type", "application/json")
                self.set_header("Access-Control-Allow-Origin", "*")
                self.write(body)
        except Exception as exc:
            self.set_status(503)
            self.write({"ok": False, "error": str(exc)})


class _MissionControlIndexHandler(tornado.web.RequestHandler):
    """Serve index.html with runtime WebSocket proxy config for prebuilt assets."""

    def initialize(self, dist_dir: str):
        self._dist_dir = Path(dist_dir)

    async def get(self, path: str = ""):
        index_path = self._dist_dir / "index.html"
        try:
            html = index_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise tornado.web.HTTPError(404)

        runtime_config = "<script>window.__LUNAR_USE_SAME_ORIGIN_WS__=true;</script>"
        if "__LUNAR_USE_SAME_ORIGIN_WS__" not in html:
            html = html.replace("<head>", f"<head>{runtime_config}", 1)
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.write(html)


def make_app(dist_dir: Path, *, mission_port: int = 8770, camera_port: int = 8767) -> tornado.web.Application:
    dist = str(dist_dir.resolve())
    return tornado.web.Application(
        [
            (r"/mission/ws", _BridgeWebSocketProxy, {"upstream_port": mission_port}),
            (r"/camera/ws/.*", _BridgeWebSocketProxy, {"upstream_port": camera_port}),
            (r"/sensor/ws", _BridgeWebSocketProxy, {"upstream_port": camera_port}),
            (r"/healthz", _HealthProxyHandler, {"upstream_port": mission_port}),
            (r"/$", _MissionControlIndexHandler, {"dist_dir": dist}),
            (
                r"/(.*)",
                tornado.web.StaticFileHandler,
                {"path": dist, "default_filename": "index.html"},
            ),
        ],
        static_hash_cache=False,
    )


def main(
    dist_dir: str | Path,
    port: int = 8501,
    host: str = "0.0.0.0",
    mission_port: int = 8770,
    camera_port: int = 8767,
) -> None:
    path = Path(dist_dir)
    if not (path / "index.html").is_file():
        raise FileNotFoundError(f"mission-control dist not found: {path / 'index.html'}")
    app = make_app(path, mission_port=mission_port, camera_port=camera_port)
    app.listen(int(port), address=host)
    print(f"mission-control static+proxy http://{host}:{port} -> bridges :{mission_port} :{camera_port}", flush=True)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve mission-control dist with WebSocket proxy")
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--mission-port", type=int, default=8770)
    parser.add_argument("--camera-port", type=int, default=8767)
    args = parser.parse_args()
    main(args.dist_dir, port=args.port, host=args.host, mission_port=args.mission_port, camera_port=args.camera_port)
