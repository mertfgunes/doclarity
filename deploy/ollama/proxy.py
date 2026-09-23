"""Auth proxy in front of Ollama.

Stock Ollama has no built-in authentication. This exists only because we
have to run it as a public Render web service (Render's free workspace
plan doesn't allow private services) - it rejects any request that
doesn't carry the shared-secret bearer token in OLLAMA_API_KEY.
"""

import http.server
import os
import socketserver
import urllib.error
import urllib.request

TOKEN = os.environ["OLLAMA_API_KEY"]
PORT = int(os.environ.get("PORT", "10000"))
UPSTREAM = "http://127.0.0.1:11434"


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _forward(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        req = urllib.request.Request(
            UPSTREAM + self.path,
            data=body,
            method=self.command,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code)
            self.end_headers()
            self.wfile.write(exc.read())
        except Exception:
            self.send_response(502)
            self.end_headers()

    def do_GET(self):
        self._forward()

    def do_POST(self):
        self._forward()

    def log_message(self, format, *args):
        pass


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    ThreadingServer(("0.0.0.0", PORT), ProxyHandler).serve_forever()
