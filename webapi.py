"""Stateless JSON API around the chess engine (pure Python, no web framework).

The browser owns the game state and sends it with every request; this module is the single source of
truth for the rules: legal moves, check, game result, and the AI's reply.

Wire formats
------------
position: {"board": [8 strings of 8 chars, rank 8 first], "turn": "white"|"black",
           "castling": "KQkq" subset, "ep": [row, col] | null}
move:     [from_row, from_col, to_row, to_col, promotion]   (promotion is a piece letter or null)
history:  list of key strings of the positions *before* the one being played from, plus that position
          itself when a move is supplied (see `play`).
"""
import json
from collections import Counter

import engine

VALID_PIECES = set(".KQRBNPkqrbnp")
MAX_HISTORY = 2000


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ------------------------------------------------------------------ (de)serialisation
def position_from_json(d):
    try:
        rows = d["board"]
        if len(rows) != 8 or any(not isinstance(r, str) or len(r) != 8 or set(r) - VALID_PIECES for r in rows):
            raise ValueError
        turn = d["turn"]
        if turn not in ("white", "black"):
            raise ValueError
        castling = frozenset(d.get("castling") or "")
        if castling - set("KQkq"):
            raise ValueError
        ep = d.get("ep")
        if ep is not None:
            ep = (int(ep[0]), int(ep[1]))
            if not engine.is_inside(*ep):
                raise ValueError
        board = [list(r) for r in rows]
    except (KeyError, TypeError, ValueError, IndexError):
        raise ApiError("invalid position")
    if engine.find_king(board, "white") is None or engine.find_king(board, "black") is None:
        raise ApiError("invalid position: both kings are required")
    return engine.Position(board, turn, castling, ep)


def position_to_json(pos):
    return {"board": ["".join(r) for r in pos.board], "turn": pos.turn,
            "castling": "".join(c for c in "KQkq" if c in pos.castling),
            "ep": list(pos.ep) if pos.ep else None}


def key_str(pos):
    board, turn, castling, ep = pos.key()
    return f"{board} {turn} {castling or '-'} {'-' if ep is None else f'{ep[0]}{ep[1]}'}"


def history_from_json(d):
    h = d.get("history", [])
    if not isinstance(h, list) or len(h) > MAX_HISTORY or any(not isinstance(k, str) for k in h):
        raise ApiError("invalid history")
    return h


def move_from_json(m):
    try:
        fr, fc, tr, tc, promo = m
        if promo is not None and (not isinstance(promo, str) or promo not in "QRBNqrbn" or len(promo) != 1):
            raise ValueError
        return (int(fr), int(fc), int(tr), int(tc), promo)
    except (TypeError, ValueError):
        raise ApiError("invalid move")


# ------------------------------------------------------------------ core
def describe(pos, prior_keys, last_move=None):
    """Full description of `pos`: everything the client needs to render and continue."""
    key = key_str(pos)
    counts = Counter(prior_keys)
    counts[key] += 1
    legal = engine.generate_moves(pos)
    in_check = engine.is_in_check(pos.board, pos.turn)
    result = engine.game_result(pos, {pos.key(): counts[key]})
    return {
        "position": position_to_json(pos),
        "key": key,
        "legal_moves": [list(m) for m in legal],
        "in_check": in_check,
        "result": result,
        "last_move": list(last_move) if last_move else None,
    }


def play(body):
    """Validate and apply a human move, or (with no `move`) describe the given position.

    `history` = keys of all earlier positions; when a move is supplied it must include the position
    the move is played from.
    """
    pos = position_from_json(body.get("position") or {})
    history = history_from_json(body)
    move = body.get("move")
    if move is None:
        return describe(pos, history)
    move = move_from_json(move)
    if move not in engine.generate_moves(pos):
        raise ApiError("illegal move", 422)
    return describe(engine.apply_move(pos, move), history, move)


def ai(body):
    """Choose and apply the AI's move for the side to move."""
    pos = position_from_json(body.get("position") or {})
    history = history_from_json(body)
    if engine.game_result(pos, {}) is not None:
        raise ApiError("game is already over", 422)
    depth = engine.AI_DEPTH
    _, move = engine.minimax(pos, depth, float("-inf"), float("inf"))
    if move is None:
        raise ApiError("no legal moves", 422)
    out = describe(engine.apply_move(pos, move), history + [key_str(pos)], move)
    out["move_text"] = engine.move_to_string(move)
    return out


ROUTES = {"/api/play": play, "/api/ai": ai}


# ------------------------------------------------------------------ HTTP glue
def run(fn, raw):
    """Parse a raw JSON request body, run `fn(body)`, and return (status, payload dict)."""
    try:
        if len(raw) > 1_000_000:
            raise ApiError("request too large", 413)
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise ApiError("body must be JSON")
        if not isinstance(body, dict):
            raise ApiError("body must be a JSON object")
        return 200, fn(body)
    except ApiError as e:
        return e.status, {"error": str(e)}
    except Exception:  # never leak a traceback to the client
        return 500, {"error": "internal error"}


def serve(handler, fn):
    """http.server adapter (used by dev_server.py): run `fn` for a BaseHTTPRequestHandler instance."""
    length = int(handler.headers.get("Content-Length") or 0)
    status, payload = run(fn, handler.rfile.read(min(length, 1_000_001)))
    data = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)
