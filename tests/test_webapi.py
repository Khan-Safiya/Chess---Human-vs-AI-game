"""Tests for the stateless JSON API (webapi.py) and its HTTP glue.

Run from the repo root:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dev_server  # noqa: E402
import webapi  # noqa: E402

START = {"board": ["rnbqkbnr", "pppppppp", "........", "........", "........", "........", "PPPPPPPP", "RNBQKBNR"],
         "turn": "white", "castling": "KQkq", "ep": None}


def mv(s, promo=None):
    f = "abcdefgh"
    return [8 - int(s[1]), f.index(s[0]), 8 - int(s[3]), f.index(s[2]), promo]


class ApiLogic(unittest.TestCase):
    def test_initial_state(self):
        d = webapi.play({"position": START, "history": []})
        self.assertEqual(len(d["legal_moves"]), 20)
        self.assertFalse(d["in_check"])
        self.assertIsNone(d["result"])

    def test_play_legal_move_and_ai_reply(self):
        d = webapi.play({"position": START, "history": [], "move": mv("e2e4")})
        self.assertEqual(d["position"]["turn"], "black")
        self.assertEqual(d["position"]["ep"], [5, 4])
        self.assertEqual(d["last_move"], mv("e2e4"))
        a = webapi.ai({"position": d["position"], "history": [webapi.key_str(webapi.position_from_json(START)), ]})
        self.assertEqual(a["position"]["turn"], "white")
        self.assertIn(a["last_move"], [list(m) for m in webapi.engine.generate_moves(
            webapi.position_from_json(d["position"]))])
        self.assertRegex(a["move_text"], r"^[a-h][1-8][a-h][1-8][QRBN]?$")

    def test_illegal_move_rejected(self):
        with self.assertRaises(webapi.ApiError) as cm:
            webapi.play({"position": START, "history": [], "move": mv("e2e5")})
        self.assertEqual(cm.exception.status, 422)

    def test_cannot_move_opponents_piece(self):
        with self.assertRaises(webapi.ApiError):
            webapi.play({"position": START, "history": [], "move": mv("e7e5")})

    def test_castling_and_promotion_over_the_wire(self):
        pos = {"board": ["r...k..r", "........", "........", "........", "........", "........", "P.......", "....K..R"],
               "turn": "white", "castling": "K", "ep": None}
        d = webapi.play({"position": pos, "history": []})
        self.assertIn(mv("e1g1"), d["legal_moves"])
        after = webapi.play({"position": pos, "history": [], "move": mv("e1g1")})
        self.assertEqual(after["position"]["board"][7], ".....RK.")
        promo = {"board": ["....k...", "P.......", "........", "........", "........", "........", "........", "....K..."],
                 "turn": "white", "castling": "", "ep": None}
        d = webapi.play({"position": promo, "history": []})
        promos = sorted(m[4] for m in d["legal_moves"] if m[:4] == mv("a7a8")[:4])
        self.assertEqual(promos, ["B", "N", "Q", "R"])

    def test_checkmate_result(self):
        pos = {"board": ["....k...", "........", "........", "........", "........", "........", "........", "R...K..."],
               "turn": "white", "castling": "", "ep": None}
        # back-rank-ish: black king e8 boxed by own pawns
        pos["board"] = ["....k...", "...ppp..", "........", "........", "........", "........", "........", "R...K..."]
        d = webapi.play({"position": pos, "history": [], "move": mv("a1a8")})
        self.assertIn("Checkmate", d["result"])
        self.assertEqual(d["legal_moves"], [])

    def test_threefold_repetition(self):
        pos = webapi.position_from_json(START)
        keys, last = [], None
        for m in ["g1f3", "g8f6", "f3g1", "f6g8"] * 2:
            d = webapi.play({"position": webapi.position_to_json(pos), "history": keys, "move": mv(m)})
            keys.append(webapi.key_str(pos))
            pos = webapi.position_from_json(d["position"])
            last = d
        self.assertIn("threefold", last["result"])

    def test_validation(self):
        bad = [{}, {"position": {"board": ["x"] * 8, "turn": "white"}},
               {"position": dict(START, turn="green")},
               {"position": dict(START, board=["........"] * 8)},      # no kings
               {"position": dict(START, castling="KX")},
               {"position": dict(START, ep=[9, 9])},
               {"position": START, "history": "nope"},
               {"position": START, "move": [1, 2, 3]}]
        for body in bad:
            with self.assertRaises(webapi.ApiError, msg=str(body)):
                webapi.play(body)


class HttpLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(dev_server.Handler, directory=dev_server.PUBLIC))
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def post(self, path, body, raw=False):
        data = body if raw else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_play_over_http(self):
        status, d = self.post("/api/play", {"position": START, "history": []})
        self.assertEqual((status, len(d["legal_moves"])), (200, 20))

    def test_ai_over_http(self):
        status, d = self.post("/api/ai", {"position": webapi.position_to_json(webapi.engine.apply_move(
            webapi.position_from_json(START), tuple(mv("e2e4")))), "history": []})
        self.assertEqual(status, 200)
        self.assertEqual(d["position"]["turn"], "white")

    def test_errors_are_json(self):
        self.assertEqual(self.post("/api/play", b"not json", raw=True)[0], 400)
        self.assertEqual(self.post("/api/play", {"position": START, "move": mv("e2e5")})[0], 422)

    def test_static_page(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as r:
            self.assertIn(b"Chess", r.read())
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/images/wK.png") as r:
            self.assertEqual(r.status, 200)


class HelpInSync(unittest.TestCase):
    """The desktop and web Help screens must describe the same rules."""

    def test_every_desktop_help_entry_is_on_the_web_page(self):
        import re
        src = open(os.path.join(dev_server.PUBLIC, "index.html"), encoding="utf-8").read()
        text = re.sub(r"<[^>]+>", "", src).replace("&amp;", "&")
        norm = lambda t: re.sub(r"[^a-z]", "", t.lower())
        page = norm(text)
        desktop = open(os.path.join(os.path.dirname(dev_server.PUBLIC), "Chess.py"), encoding="utf-8").read()
        block = desktop[desktop.index("HELP_RULES = ["):desktop.index("_help_cache")]
        entries = re.findall(r'\("([^"]*)",\s*((?:"[^"]*"\s*)*)\)', block)
        self.assertGreaterEqual(len(entries), 18)
        for head, body in entries:
            joined = head + "".join(re.findall(r'"([^"]*)"', body))
            if head.strip() in ("Pieces:", "Special Rules:"):
                joined = head
            if head in ("  Pawn:",):                      # web adds a space: "square (or"
                joined = joined.replace("square(or", "square or")
            self.assertIn(norm(joined).replace("squareor", "squareor"), page, msg=head)


if __name__ == "__main__":
    unittest.main()
