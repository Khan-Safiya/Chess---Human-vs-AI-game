"""Vercel serverless function: POST /api/play (logic lives in webapi.py)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import webapi  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        webapi.serve(self, webapi.play)

    def log_message(self, *args):
        pass
