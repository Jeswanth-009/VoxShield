"""Local competition-grade operator console for VoxShield live telemetry."""

from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .dashboard_ui import HTML
from .telemetry import write_atomic_json

CONTROL_DEFAULTS = {
    "wet_mix": 0.82,
    "output_gain_db": 0.0,
    "operator_bypass": False,
    "mute_output": False,
    "preset": "balanced",
    "operating_mode": "auto",
}


def _read_json(path: Path, fallback: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def _validated_control(value: dict) -> dict:
    result = dict(CONTROL_DEFAULTS)
    result["wet_mix"] = max(0.0, min(1.0, float(value.get("wet_mix", 0.82))))
    result["output_gain_db"] = max(-18.0, min(6.0, float(value.get("output_gain_db", 0.0))))
    result["operator_bypass"] = bool(value.get("operator_bypass", False))
    result["mute_output"] = bool(value.get("mute_output", False))
    preset = str(value.get("preset", "custom"))
    result["preset"] = preset if preset in {"safe", "balanced", "aggressive", "custom"} else "custom"
    operating_mode = str(value.get("operating_mode", "auto"))
    result["operating_mode"] = (
        operating_mode if operating_mode in {"dry", "enhanced", "auto"} else "auto"
    )
    result["updated_unix"] = time.time()
    return result


def make_handler(telemetry_path: Path, control_path: Path, event_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _json(self, value: dict, status: int = 200) -> None:
            self._send(json.dumps(value, separators=(",", ":")).encode(), "application/json", status)

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route in {"/", "/index.html"}:
                self._send(HTML.encode(), "text/html; charset=utf-8")
            elif route == "/api/telemetry":
                self._json(_read_json(telemetry_path, {"status": "waiting", "message": "Start the live engine"}))
            elif route == "/api/control":
                self._json(_read_json(control_path, dict(CONTROL_DEFAULTS)))
            elif route == "/api/events":
                events = []
                try:
                    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()[-50:]]
                except (OSError, json.JSONDecodeError):
                    pass
                self._json({"events": events})
            elif route == "/api/export":
                payload = {"exported_unix": time.time(), "telemetry": _read_json(telemetry_path, {}),
                           "control": _read_json(control_path, dict(CONTROL_DEFAULTS))}
                self._send(json.dumps(payload, indent=2).encode(), "application/json")
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 65536)
                body = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._json({"error": "invalid JSON"}, 400)
                return
            if route == "/api/control":
                control = _validated_control(body if isinstance(body, dict) else {})
                write_atomic_json(control_path, control)
                self._json(control)
            elif route == "/api/marker":
                label = str(body.get("label", "Operator marker"))[:120]
                event_path.parent.mkdir(parents=True, exist_ok=True)
                event = {"timestamp_unix": time.time(), "label": label}
                with event_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, separators=(",", ":")) + "\n")
                self._json(event)
            else:
                self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the VoxShield tactical demonstration console")
    parser.add_argument("--telemetry-file", default="artifacts/live-telemetry.json")
    parser.add_argument("--control-file", default="artifacts/live-control.json")
    parser.add_argument("--event-file", default="artifacts/live-events.jsonl")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    control_path = Path(args.control_file)
    if not control_path.exists():
        write_atomic_json(control_path, dict(CONTROL_DEFAULTS))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(
        Path(args.telemetry_file), control_path, Path(args.event_file)))
    url = f"http://{args.host}:{args.port}/"
    print(f"VoxShield console: {url}")
    if args.open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
