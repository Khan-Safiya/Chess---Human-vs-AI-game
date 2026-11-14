"""Chess engine: position, rules, and minimax AI. Pure Python, no pygame.

Used by the desktop UI (Chess.py) and the web API (webapi.py / api/*.py).
"""
import math

AI_DEPTH = 3

PIECE_VALUES = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}
PROMOTION_CHOICES = ['Q', 'R', 'B', 'N']

KNIGHT_JUMPS = [(2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1)]
ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
KING_DIRS = ROOK_DIRS + BISHOP_DIRS


# ------------------------------------------------------------------ position
class Position:
    """Immutable-by-convention game state: board, side to move, castling rights, en-passant square.

    A move is a tuple (from_row, from_col, to_row, to_col, promotion). Castling is a king move of
    two columns; en passant is a pawn moving diagonally onto `ep`; `promotion` is a piece char or None.
    """
    __slots__ = ('board', 'turn', 'castling', 'ep')

    def __init__(self, board, turn, castling, ep):
        self.board = board
        self.turn = turn
        self.castling = castling      # frozenset of 'K','Q' (white) / 'k','q' (black)
        self.ep = ep                  # (row, col) of the square a pawn may capture onto, or None

    def key(self):
        return (''.join(''.join(r) for r in self.board), self.turn,
                ''.join(sorted(self.castling)), self.ep)


def init_board():
    return [list("rnbqkbnr"), list("pppppppp"), list("........"), list("........"),
            list("........"), list("........"), list("PPPPPPPP"), list("RNBQKBNR")]


def init_position():
    return Position(init_board(), 'white', frozenset("KQkq"), None)


def other(color):
    return 'black' if color == 'white' else 'white'


def is_inside(row, col):
    return 0 <= row < 8 and 0 <= col < 8


def is_enemy(piece, color):
    if piece == '.':
        return False
    return piece.islower() if color == 'white' else piece.isupper()


def is_friend(piece, color):
    if piece == '.':
        return False
    return piece.isupper() if color == 'white' else piece.islower()


def apply_move(pos, move):
    """Return the new Position after `move` (handles castling, en passant, promotion, rights)."""
    fr, fc, tr, tc, promo = move
    b = [row[:] for row in pos.board]
    piece = b[fr][fc]
    target = b[tr][tc]
    castling = set(pos.castling)
    ep = None
    b[fr][fc] = '.'
    if piece.upper() == 'P' and fc != tc and target == '.' and (tr, tc) == pos.ep:
        b[fr][tc] = '.'                                   # en passant: remove the passed pawn
    b[tr][tc] = promo if promo else piece
    if piece.upper() == 'K':
        if abs(tc - fc) == 2:                             # castling: also move the rook
            if tc > fc:
                b[tr][5], b[tr][7] = b[tr][7], '.'
            else:
                b[tr][3], b[tr][0] = b[tr][0], '.'
        castling -= {'K', 'Q'} if piece == 'K' else {'k', 'q'}
    for (r, c), flag in (((7, 0), 'Q'), ((7, 7), 'K'), ((0, 0), 'q'), ((0, 7), 'k')):
        if (fr, fc) == (r, c) or (tr, tc) == (r, c):      # rook moved or was captured
            castling.discard(flag)
    if piece.upper() == 'P' and abs(tr - fr) == 2:
        ep = ((fr + tr) // 2, fc)
    return Position(b, other(pos.turn), frozenset(castling), ep)


def find_king(board, color):
    king = 'K' if color == 'white' else 'k'
    for i in range(8):
        for j in range(8):
            if board[i][j] == king:
                return (i, j)
    return None


def is_square_attacked(board, row, col, attacker_color):
    """True if (row, col) is attacked by any piece of attacker_color."""
    white = attacker_color == 'white'
    pawn, knight, king = ('P', 'N', 'K') if white else ('p', 'n', 'k')
    rook_like = ('R', 'Q') if white else ('r', 'q')
    bishop_like = ('B', 'Q') if white else ('b', 'q')
    pr = row + 1 if white else row - 1          # a white pawn attacks upward, so it sits below
    for dc in (-1, 1):
        if is_inside(pr, col + dc) and board[pr][col + dc] == pawn:
            return True
    for dr, dc in KNIGHT_JUMPS:
        r, c = row + dr, col + dc
        if is_inside(r, c) and board[r][c] == knight:
            return True
    for dirs, pieces in ((ROOK_DIRS, rook_like), (BISHOP_DIRS, bishop_like)):
        for dr, dc in dirs:
            r, c = row + dr, col + dc
            while is_inside(r, c):
                p = board[r][c]
                if p != '.':
                    if p in pieces:
                        return True
                    break
                r += dr
                c += dc
    for dr, dc in KING_DIRS:
        r, c = row + dr, col + dc
        if is_inside(r, c) and board[r][c] == king:
            return True
    return False


def is_in_check(board, color):
    king_pos = find_king(board, color)
    if not king_pos:
        return True
    return is_square_attacked(board, king_pos[0], king_pos[1], other(color))


def generate_pawn_moves(pos, i, j, color):
    board = pos.board
    direction, start_row, promo_row = (-1, 6, 0) if color == 'white' else (1, 1, 7)
    moves = []

    def add(to_r, to_c):
        if to_r == promo_row:
            for p in PROMOTION_CHOICES:
                moves.append((i, j, to_r, to_c, p if color == 'white' else p.lower()))
        else:
            moves.append((i, j, to_r, to_c, None))

    ni = i + direction
    if is_inside(ni, j) and board[ni][j] == '.':
        add(ni, j)
        n2 = i + 2 * direction
        if i == start_row and board[n2][j] == '.':
            add(n2, j)
    for dj in (-1, 1):
        nj = j + dj
        if not is_inside(ni, nj):
            continue
        if is_enemy(board[ni][nj], color) or (board[ni][nj] == '.' and (ni, nj) == pos.ep):
            add(ni, nj)
    return moves


def generate_step_moves(board, i, j, color, offsets):
    moves = []
    for dr, dc in offsets:
        r, c = i + dr, j + dc
        if is_inside(r, c) and not is_friend(board[r][c], color):
            moves.append((i, j, r, c, None))
    return moves


def generate_sliding_moves(board, i, j, color, directions):
    moves = []
    for dr, dc in directions:
        r, c = i + dr, j + dc
        while is_inside(r, c):
            target = board[r][c]
            if target == '.':
                moves.append((i, j, r, c, None))
            else:
                if is_enemy(target, color):
                    moves.append((i, j, r, c, None))
                break
            r += dr
            c += dc
    return moves


def generate_castling_moves(pos, color):
    board = pos.board
    row = 7 if color == 'white' else 0
    king, rook = ('K', 'R') if color == 'white' else ('k', 'r')
    ks, qs = ('K', 'Q') if color == 'white' else ('k', 'q')
    enemy = other(color)
    if board[row][4] != king or is_square_attacked(board, row, 4, enemy):
        return []
    moves = []
    if (ks in pos.castling and board[row][7] == rook and board[row][5] == '.' and board[row][6] == '.'
            and not is_square_attacked(board, row, 5, enemy) and not is_square_attacked(board, row, 6, enemy)):
        moves.append((row, 4, row, 6, None))
    if (qs in pos.castling and board[row][0] == rook
            and all(board[row][c] == '.' for c in (1, 2, 3))
            and not is_square_attacked(board, row, 3, enemy) and not is_square_attacked(board, row, 2, enemy)):
        moves.append((row, 4, row, 2, None))
    return moves


def generate_piece_moves(pos, i, j, color):
    """Pseudo-legal moves (king safety not yet checked) for the piece at (i, j)."""
    board = pos.board
    kind = board[i][j].upper()
    if kind == 'P':
        return generate_pawn_moves(pos, i, j, color)
    if kind == 'N':
        return generate_step_moves(board, i, j, color, KNIGHT_JUMPS)
    if kind == 'B':
        return generate_sliding_moves(board, i, j, color, BISHOP_DIRS)
    if kind == 'R':
        return generate_sliding_moves(board, i, j, color, ROOK_DIRS)
    if kind == 'Q':
        return generate_sliding_moves(board, i, j, color, KING_DIRS)
    return generate_step_moves(board, i, j, color, KING_DIRS) + generate_castling_moves(pos, color)


def generate_moves(pos):
    """All legal moves for pos.turn."""
    color = pos.turn
    pseudo = []
    for i in range(8):
        for j in range(8):
            if is_friend(pos.board[i][j], color):
                pseudo.extend(generate_piece_moves(pos, i, j, color))
    return [m for m in pseudo if not is_in_check(apply_move(pos, m).board, color)]


def insufficient_material(board):
    """K v K, K+minor v K, or only same-coloured bishops."""
    minors = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p in ('.', 'K', 'k'):
                continue
            if p.upper() in ('P', 'R', 'Q'):
                return False
            minors.append((p, r, c))
    if len(minors) <= 1:
        return True
    if all(p.upper() == 'B' for p, _, _ in minors):
        return len({(r + c) % 2 for _, r, c in minors}) == 1
    return False


def game_result(pos, history):
    """Return a final message if the game is over for pos (side to move), else None."""
    if not generate_moves(pos):
        if is_in_check(pos.board, pos.turn):
            return f"Checkmate! {'Black' if pos.turn == 'white' else 'White'} wins."
        return "Stalemate! Draw."
    if insufficient_material(pos.board):
        return "Draw by insufficient material!"
    if history.get(pos.key(), 0) >= 3:
        return "Draw by threefold repetition!"
    return None


# ------------------------------------------------------------------------ AI
def evaluate_board(board):
    """Material balance: positive favours White."""
    score = 0
    for row in board:
        for piece in row:
            if piece != '.':
                v = PIECE_VALUES[piece.upper()]
                score += v if piece.isupper() else -v
    return score


def order_moves(pos, moves):
    """Captures (most valuable victim first) and promotions first, to improve pruning."""
    def score(m):
        victim = pos.board[m[2]][m[3]]
        s = PIECE_VALUES[victim.upper()] * 10 if victim != '.' else 0
        return s + (50 if m[4] else 0)
    return sorted(moves, key=score, reverse=True)


def minimax(pos, depth, alpha, beta):
    """Alpha-beta minimax. White maximises, Black minimises. Returns (score, best_move)."""
    moves = generate_moves(pos)
    if not moves:
        if is_in_check(pos.board, pos.turn):          # prefer faster mates
            return (-1000 - depth if pos.turn == 'white' else 1000 + depth), None
        return 0, None
    if depth == 0:
        return evaluate_board(pos.board), None
    best_move = None
    if pos.turn == 'white':
        best = -math.inf
        for m in order_moves(pos, moves):
            score, _ = minimax(apply_move(pos, m), depth - 1, alpha, beta)
            if score > best:
                best, best_move = score, m
            alpha = max(alpha, score)
            if beta <= alpha:
                break
    else:
        best = math.inf
        for m in order_moves(pos, moves):
            score, _ = minimax(apply_move(pos, m), depth - 1, alpha, beta)
            if score < best:
                best, best_move = score, m
            beta = min(beta, score)
            if beta <= alpha:
                break
    return best, best_move


def move_to_string(move):
    fr, fc, tr, tc, promo = move
    s = 'abcdefgh'[fc] + str(8 - fr) + 'abcdefgh'[tc] + str(8 - tr)
    return s + promo.upper() if promo else s
