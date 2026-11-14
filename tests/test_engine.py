"""Engine tests. Run from the repo root:  python -m unittest discover -s tests -v

Perft node counts are the standard chess-programming reference numbers; matching them proves
move generation (incl. castling, en passant, promotion, pins) is correct.
"""
import math
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine as C  # noqa: E402


def from_fen(fen):
    parts = fen.split()
    board = []
    for rank in parts[0].split('/'):
        row = []
        for ch in rank:
            row.extend('.' * int(ch) if ch.isdigit() else ch)
        board.append(row)
    turn = 'white' if parts[1] == 'w' else 'black'
    castling = frozenset(c for c in parts[2] if c != '-')
    ep = None
    if parts[3] != '-':
        ep = (8 - int(parts[3][1]), 'abcdefgh'.index(parts[3][0]))
    return C.Position(board, turn, castling, ep)


def perft(pos, depth):
    if depth == 0:
        return 1
    return sum(perft(C.apply_move(pos, m), depth - 1) for m in C.generate_moves(pos))


def mv(s, promo=None):
    f = 'abcdefgh'
    return (8 - int(s[1]), f.index(s[0]), 8 - int(s[3]), f.index(s[2]), promo)


class Perft(unittest.TestCase):
    def test_start(self):
        pos = C.init_position()
        self.assertEqual([perft(pos, d) for d in (1, 2, 3)], [20, 400, 8902])

    def test_kiwipete_castling_ep(self):
        pos = from_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
        self.assertEqual([perft(pos, d) for d in (1, 2)], [48, 2039])

    def test_endgame_ep_pins(self):
        pos = from_fen("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1")
        self.assertEqual([perft(pos, d) for d in (1, 2, 3)], [14, 191, 2812])

    def test_promotions(self):
        pos = from_fen("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1")
        self.assertEqual([perft(pos, d) for d in (1, 2)], [6, 264])


class SpecialMoves(unittest.TestCase):
    def test_castling_moves_rook(self):
        pos = from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        moves = C.generate_moves(pos)
        self.assertIn(mv("e1g1"), moves)
        self.assertIn(mv("e1c1"), moves)
        after = C.apply_move(pos, mv("e1g1"))
        self.assertEqual((after.board[7][6], after.board[7][5], after.board[7][7]), ('K', 'R', '.'))
        self.assertNotIn('K', after.castling)
        self.assertNotIn('Q', after.castling)

    def test_no_castling_through_check(self):
        pos = from_fen("4k3/8/8/8/8/8/5r2/R3K2R w KQ - 0 1")   # rook attacks f1
        self.assertNotIn(mv("e1g1"), C.generate_moves(pos))
        self.assertIn(mv("e1c1"), C.generate_moves(pos))

    def test_no_castling_out_of_check(self):
        pos = from_fen("4k3/8/8/8/8/8/4r3/R3K2R w KQ - 0 1")
        moves = C.generate_moves(pos)
        self.assertNotIn(mv("e1g1"), moves)
        self.assertNotIn(mv("e1c1"), moves)

    def test_rook_capture_removes_right(self):
        pos = from_fen("r3k2r/8/8/8/8/8/6B1/R3K2R w KQkq - 0 1")
        after = C.apply_move(pos, mv("g2a8"))
        self.assertNotIn('q', after.castling)
        self.assertIn('k', after.castling)

    def test_en_passant(self):
        pos = from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        self.assertIn(mv("e5d6"), C.generate_moves(pos))
        after = C.apply_move(pos, mv("e5d6"))
        self.assertEqual(after.board[3][3], '.')        # captured pawn removed
        self.assertEqual(after.board[2][3], 'P')

    def test_en_passant_only_immediately(self):
        pos = C.init_position()
        for m in ("e2e4", "a7a6", "e4e5", "d7d5"):
            pos = C.apply_move(pos, mv(m))
        self.assertEqual(pos.ep, (2, 3))
        self.assertIn(mv("e5d6"), C.generate_moves(pos))
        pos = C.apply_move(pos, mv("h2h3"))
        pos = C.apply_move(pos, mv("h7h6"))
        self.assertNotIn(mv("e5d6"), C.generate_moves(pos))

    def test_four_promotion_choices(self):
        pos = from_fen("8/P3k3/8/8/8/8/8/4K3 w - - 0 1")
        promos = sorted(m[4] for m in C.generate_moves(pos) if m[:4] == mv("a7a8")[:4])
        self.assertEqual(promos, ['B', 'N', 'Q', 'R'])
        after = C.apply_move(pos, mv("a7a8", 'N'))
        self.assertEqual(after.board[0][0], 'N')


class GameRules(unittest.TestCase):
    def test_fools_mate(self):
        pos = C.init_position()
        for m in ("f2f3", "e7e5", "g2g4", "d8h4"):
            pos = C.apply_move(pos, mv(m))
        self.assertIn("Checkmate", C.game_result(pos, {}))

    def test_stalemate(self):
        pos = from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertIn("Stalemate", C.game_result(pos, {}))

    def test_insufficient_material(self):
        self.assertTrue(C.insufficient_material(from_fen("8/8/4k3/8/8/3K4/8/8 w - - 0 1").board))
        self.assertFalse(C.insufficient_material(from_fen("8/8/4k3/8/8/3KP3/8/8 w - - 0 1").board))

    def test_ai_takes_mate_in_one(self):
        pos = from_fen("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1")
        _, move = C.minimax(pos, 3, -math.inf, math.inf)
        self.assertEqual(move, mv("a1a8"))

    def test_ai_returns_legal_move(self):
        _, move = C.minimax(C.apply_move(C.init_position(), mv("e2e4")), 2, -math.inf, math.inf)
        self.assertIn(move, C.generate_moves(C.apply_move(C.init_position(), mv("e2e4"))))


if __name__ == "__main__":
    unittest.main()
