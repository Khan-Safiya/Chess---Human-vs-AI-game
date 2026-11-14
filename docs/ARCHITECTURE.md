# Architecture

The code is split so the rules and AI are shared by two front-ends:

```
engine.py  <--  Chess.py (pygame desktop UI)
    ^
    +-------  webapi.py  <--  api/play.py, api/ai.py (Vercel)  and  dev_server.py (local)
                                  ^
                           public/index.html (browser UI, calls /api/*)
```

Sections 1-3 describe `engine.py`; section 4 the desktop UI in `Chess.py`; section 5 the web version.

## 1. Position

`Position(board, turn, castling, ep)` is the complete game state and is treated as immutable.

- `board`: 8×8 list of single characters. Uppercase = White (`K Q R B N P`), lowercase = Black, `.` = empty.
  Row 0 is rank 8; row 7 is rank 1; column 0 is file `a`.
- `turn`: `'white'` or `'black'`.
- `castling`: `frozenset` of remaining rights, `K`/`Q` (White king/queen side), `k`/`q` (Black).
- `ep`: `(row, col)` of the en-passant target square, or `None`. Set only for one ply after a double pawn push.
- `Position.key()` gives a hashable identity (board + turn + rights + ep) used for threefold repetition,
  so positions that differ in castling rights or en-passant availability are correctly distinct.

A **move** is a tuple `(from_row, from_col, to_row, to_col, promotion)`. No extra flags are needed:

- *castling* = a king moving two columns (the rook is moved by `apply_move`);
- *en passant* = a pawn moving diagonally onto an empty `pos.ep` square (the passed pawn is removed);
- *promotion* = the promoted piece character (a pawn reaching the last rank generates four moves, Q/R/B/N).

`apply_move(pos, move)` returns a new `Position`, updating castling rights (king/rook moved, rook captured)
and the en-passant square. Search never mutates a board.

## 2. Rules engine

| Function | Role |
|---|---|
| `generate_piece_moves` and `generate_{pawn,step,sliding,castling}_moves` | Pseudo-legal moves per piece |
| `generate_moves(pos)` | Legal moves for `pos.turn`: pseudo-legal moves filtered by "own king not in check afterwards" |
| `generate_castling_moves` | Requires rights, empty squares, rook present, and king not in / passing through / landing in check |
| `is_square_attacked`, `is_in_check`, `find_king` | Attack and check detection |
| `insufficient_material` | K v K, K+minor v K, same-colour bishops |
| `game_result(pos, history)` | Final message (checkmate / stalemate / insufficient material / threefold repetition) or `None` |

Not implemented: fifty-move rule.

## 3. AI

`minimax(pos, depth, alpha, beta)` — alpha-beta search; White maximises and Black minimises `evaluate_board`
(material: P=1, N=B=3, R=5, Q=9). Terminal positions score ±(1000+depth) for mate (so faster mates are preferred)
or 0 for stalemate. `order_moves` searches captures (high-value victims first) and promotions first to improve pruning.
The AI uses `AI_DEPTH = 3`.

## 4. UI / game loop

`main()` keeps all state in one dict `S`: `pos`, `history` (position-key → count), `undo_stack`, `last_move`,
`selected`, `valid_moves`, `pending_promo`, `over`, `ai`, `message`.

Each frame:

1. **Events** — Help/Back, New Game, Undo (`U`), Restart (`R`); board clicks only when it is White's turn and the game isn't over.
   Selecting a destination with several matching moves (promotion) opens the promotion picker.
2. **AI** — when it is Black's turn and no search is running, a daemon thread runs `minimax` and writes its move into
   a small result dict `S['ai']`. The main loop polls that dict and plays the move when ready, so rendering and input
   keep running during the search.
3. **Render** — `draw_game` (board, highlights, bottom panel, optional promotion overlay) or `draw_help_screen`; 60 FPS.

### Undo and cancellation

Before each human move a snapshot `(pos, history copy, last_move)` is pushed to `undo_stack`. Undo pops one snapshot,
which reverts both the human move and the AI reply (or cancels the human move if the AI is still thinking).
Setting `S['ai'] = None` orphans any running search thread: it finishes on its own and writes into a dict nobody reads.
New Game works the same way.

## 5. Web version (Vercel)

`webapi.py` exposes two pure functions plus HTTP glue (`serve`), so it is testable without a server:

| Endpoint | Request | Response |
|---|---|---|
| `POST /api/play` | `{position, history, move?}` | Validates and applies the human move (or, with no `move`, just describes the position) |
| `POST /api/ai` | `{position, history}` | Runs `minimax` and applies the AI's move; adds `move_text` |

Both return `{position, key, legal_moves, in_check, result, last_move}`. Wire formats are documented at the top of
`webapi.py`: positions are 8 row-strings + turn + castling string + en-passant square; moves are
`[from_row, from_col, to_row, to_col, promotion]`. Illegal moves are rejected with 422, malformed input with 400.

**Stateless by design** - serverless functions remember nothing, so the browser keeps a stack of the server's responses.
That stack *is* the undo history (Undo pops one or two entries), and `history` (the list of position keys) lets the server
count repetitions for the threefold-repetition draw. The browser contains no chess rules: it only draws the board and
sends clicks. `api/*.py` are thin `BaseHTTPRequestHandler` wrappers (Vercel's Python runtime); `dev_server.py` serves
the same routes locally.
