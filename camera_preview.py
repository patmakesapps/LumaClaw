"""Preview a Linux camera locally or through a browser over SSH."""

import argparse
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import shutil
import subprocess
import sys


PAGE = b"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LumaClaw Camera</title>
<style>
  body { margin: 0; background: #171717; color: white; font: 16px sans-serif;
         text-align: center; }
  h1 { font-size: 1.2rem; margin: 1rem; }
  img { display: block; max-width: 100vw; max-height: calc(100vh - 4rem);
        margin: auto; }
</style>
<h1>LumaClaw Camera</h1>
<img src="/stream" alt="Live camera feed">
</html>
"""


def serve_camera(device: str, port: int) -> None:
    class CameraHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(PAGE)))
                self.end_headers()
                self.wfile.write(PAGE)
                return

            if self.path != "/stream":
                self.send_error(404)
                return

            command = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-f", "v4l2", "-i", device,
                "-vf", "fps=15,scale=640:-2",
                "-an", "-c:v", "mjpeg", "-q:v", "6",
                "-f", "mpjpeg", "pipe:1",
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=ffmpeg")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                while chunk := process.stdout.read1(65536):
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                process.stdout.close()

    server = ThreadingHTTPServer(("127.0.0.1", port), CameraHandler)
    print(f"Camera server running on http://127.0.0.1:{port}", flush=True)
    print("Forward this port over SSH, then open that URL on your computer.", flush=True)
    print("Press Ctrl+C here to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the camera feed locally or in a browser over SSH.")
    parser.add_argument(
        "--device",
        help="Camera device, such as /dev/video2 (default: first /dev/video* device)",
    )
    parser.add_argument("--port", type=int, default=8765, help="Browser preview port (default: 8765)")
    parser.add_argument("--web", action="store_true", help="Use browser preview even with a desktop display")
    args = parser.parse_args()

    web_mode = args.web or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    player = "ffmpeg" if web_mode else "ffplay"
    if shutil.which(player) is None:
        print(f"{player} is required. Install FFmpeg on the computer with the camera.", file=sys.stderr)
        return 1

    devices = sorted(glob.glob("/dev/video*"))
    device = args.device or (devices[0] if devices else None)
    if device is None or not os.path.exists(device):
        print("No camera device found. Connect the camera and check for /dev/video*.", file=sys.stderr)
        return 1

    if web_mode:
        try:
            serve_camera(device, args.port)
        except OSError as exc:
            print(f"Could not start camera server: {exc}", file=sys.stderr)
            return 1
        return 0

    print(f"Opening {device}. Press q in the video window to quit.")
    command = [
        "ffplay",
        "-hide_banner",
        "-loglevel", "error",
        "-window_title", "LumaClaw Camera",
        "-f", "v4l2",
        "-i", device,
    ]
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
