"""Local server that mirrors the Vercel deployment: static files from public/ plus the /api routes.

    python dev_server.py [port]      ->  http://localhost:8000
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import webapi

PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        fn = webapi.ROUTES.get(self.path.split("?")[0])
        if fn is None:
            self.send_error(404)
        else:
            webapi.serve(self, fn)

    def log_message(self, fmt, *args):
        if self.command == "POST" or "favicon" not in self.path:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=PUBLIC))
    print(f"Serving on http://localhost:{port}")
    server.serve_forever()
