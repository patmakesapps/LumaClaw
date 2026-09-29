"""Manual claw controls in a browser, reachable through an SSH tunnel."""

import argparse
from contextlib import contextmanager
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import secrets
import threading
from urllib.parse import parse_qs

from scservo_sdk import COMM_SUCCESS, PortHandler, sms_sts


BAUDRATE = 1_000_000
CLAW_OPEN = 2825
CLAW_CLOSED = 3025
SPEED = 200
ACCELERATION = 50
PRESENT_LOAD_ADDRESS = 60


@contextmanager
def connected_servo(serial_port: str):
    port = PortHandler(serial_port)
    if not port.openPort():
        raise RuntimeError(f"Could not open {serial_port}")
    try:
        if not port.setBaudRate(BAUDRATE):
            raise RuntimeError(f"Could not set baud rate to {BAUDRATE}")
        yield sms_sts(port)
    finally:
        port.closePort()


def write_position(servo, servo_id: int, position: int) -> None:
    result, error = servo.WritePosEx(servo_id, position, SPEED, ACCELERATION)
    if result != COMM_SUCCESS or error:
        raise RuntimeError(f"Servo command failed (result={result}, error={error})")


def read_feedback(servo, servo_id: int) -> tuple[int, int]:
    position, result, error = servo.ReadPos(servo_id)
    if result != COMM_SUCCESS or error:
        raise RuntimeError(f"Position read failed (result={result}, error={error})")
    raw_load, result, error = servo.read2ByteTxRx(servo_id, PRESENT_LOAD_ADDRESS)
    if result != COMM_SUCCESS or error:
        raise RuntimeError(f"Load read failed (result={result}, error={error})")
    return position, raw_load & 0x3FF


def move_claw(serial_port: str, servo_id: int, position: int) -> None:
    with connected_servo(serial_port) as servo:
        write_position(servo, servo_id, position)


def page(message: str = "", is_error: bool = False, token: str = "") -> bytes:
    message_html = (
        f'<p class="{"error" if is_error else "status"}">{escape(message)}</p>'
        if message else ""
    )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LumaClaw Control</title>
<style>
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
         background: #171923; color: #f7f8fa; font: 18px system-ui, sans-serif; }}
  main {{ width: min(90vw, 420px); text-align: center; }}
  h1 {{ font-size: 1.6rem; }}
  .buttons {{ display: flex; gap: 1rem; justify-content: center; margin: 2rem 0; }}
  button {{ min-width: 130px; padding: 1rem; border: 0; border-radius: 12px;
            font: inherit; font-weight: 700; cursor: pointer; }}
  .open {{ background: #78d8b0; }}
  .close {{ background: #ffb378; }}
  .feedback {{ background: #d7dbe5; }}
  .status {{ color: #78d8b0; }}
  .error {{ color: #ff9c9c; }}
</style>
<main>
  <h1>LumaClaw</h1>
  <p>Manual claw controls</p>
  <div class="buttons">
    <form method="post" action="/move">
      <input type="hidden" name="token" value="{token}">
      <button class="open" name="action" value="open">Open</button>
    </form>
    <form method="post" action="/move">
      <input type="hidden" name="token" value="{token}">
      <button class="close" name="action" value="close">Close fully</button>
    </form>
  </div>
  <div class="buttons">
    <form method="post" action="/move">
      <input type="hidden" name="token" value="{token}">
      <button class="feedback" name="action" value="feedback">Read feedback</button>
    </form>
  </div>
  {message_html}
</main>
</html>
""".encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve manual claw controls over SSH.")
    parser.add_argument("--serial-port", default="/dev/ttyACM0")
    parser.add_argument("--servo-id", type=int, default=1)
    parser.add_argument("--port", type=int, default=8766, help="Local web port (default: 8766)")
    args = parser.parse_args()
    token = secrets.token_urlsafe(24)
    move_lock = threading.Lock()

    class ClawHandler(BaseHTTPRequestHandler):
        def respond(self, status: int, message: str = "", is_error: bool = False) -> None:
            body = page(message, is_error, token)
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                self.respond(200)
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            if self.path != "/move":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if not 0 < length <= 256:
                self.send_error(400)
                return
            fields = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            supplied_token = fields.get("token", [""])[0]
            if not hmac.compare_digest(supplied_token, token):
                self.send_error(403)
                return
            action = fields.get("action", [""])[0]
            if action not in ("open", "close", "feedback"):
                self.send_error(400)
                return
            try:
                with move_lock:
                    if action == "feedback":
                        with connected_servo(args.serial_port) as servo:
                            position, load = read_feedback(servo, args.servo_id)
                        message = f"Position: {position}; load: {load}/1000."
                    else:
                        position = CLAW_OPEN if action == "open" else CLAW_CLOSED
                        move_claw(args.serial_port, args.servo_id, position)
                        message = f"Claw {action} command sent."
            except Exception as exc:
                self.respond(503, f"Could not {action} claw: {exc}", True)
                return
            self.respond(200, message)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), ClawHandler)
    print(f"Claw controls running at http://127.0.0.1:{args.port}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
