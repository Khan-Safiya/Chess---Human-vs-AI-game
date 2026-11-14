"""WSGI entrypoint for Vercel (and any WSGI server): `app` serves the JSON API and the static site.

Vercel's Python runtime looks for a module-level `app` in a default location such as this file.
Routes:  POST /api/play, POST /api/ai   -> webapi (pure-Python chess engine)
         everything else                -> files from public/ (normally served by the Vercel CDN already;
                                           handled here too so the app also works standalone)
"""
import json
import mimetypes
import os

import webapi

PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 413: "Payload Too Large",
           422: "Unprocessable Entity", 500: "Internal Server Error"}


def _respond(start_response, status, body, content_type, extra=()):
    headers = [("Content-Type", content_type), ("Content-Length", str(len(body))), *extra]
    start_response(status, headers)
    return [body]


def _json(start_response, code, payload, extra=()):
    return _respond(start_response, f"{code} {REASONS.get(code, 'Error')}", json.dumps(payload).encode(),
                    "application/json", [("Cache-Control", "no-store"), *extra])


def _static(start_response, path):
    rel = "index.html" if path in ("", "/") else path.lstrip("/")
    root = os.path.realpath(PUBLIC)
    full = os.path.realpath(os.path.join(root, rel))
    if not full.startswith(root + os.sep) or not os.path.isfile(full):
        return _json(start_response, 404, {"error": "not found"})
    with open(full, "rb") as f:
        body = f.read()
    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    return _respond(start_response, "200 OK", body, ctype)


def app(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET")
    fn = webapi.ROUTES.get(path.rstrip("/") or "/")
    if fn is None:
        if method not in ("GET", "HEAD"):
            return _json(start_response, 405, {"error": "method not allowed"}, [("Allow", "GET, HEAD")])
        return _static(start_response, path)
    if method != "POST":
        return _json(start_response, 405, {"error": "use POST"}, [("Allow", "POST")])
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    raw = environ["wsgi.input"].read(min(length, 1_000_001)) if length > 0 else b""
    status, payload = webapi.run(fn, raw)
    return _json(start_response, status, payload)
