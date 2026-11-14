# Development notes

## Running the tests

```bash
python -m unittest discover -s tests -v
```

`tests/test_webapi.py` tests the JSON API logic and spins up `dev_server`'s handler on a random port to test the HTTP layer
(status codes, JSON errors, static files). `tests/test_engine.py` contains:

- **Perft** — node counts for the start position and three standard stress positions (Kiwipete for castling/en passant,
  an endgame with pins and en passant, and a promotion-heavy position). If these match the published numbers,
  move generation is correct.
- **Special moves** — castling (rook moves, rights removed, not through/out of check, rook capture removes right),
  en passant (only immediately after the double push), four promotion choices.
- **Game rules** — fool's mate, stalemate, insufficient material.
- **AI** — finds mate in one, always returns a legal move.

pygame runs without a display in tests via `SDL_VIDEODRIVER=dummy`.

## Running the website locally

`python dev_server.py [port]` serves `public/` and the `/api` routes exactly as Vercel will.

## Headless smoke test of the desktop UI

Set `SDL_VIDEODRIVER=dummy`, monkey-patch `pygame.mouse.get_pos`, post `MOUSEBUTTONDOWN` events (with `pos=`) from a wrapper
around `pygame.display.flip`, save screenshots with `pygame.image.save(pygame.display.get_surface(), ...)`, then post `QUIT`.

## Ideas for extension

1. Piece-square tables and a quiescence search for a noticeably stronger AI; iterative deepening with a time limit.
2. Colour choice (play Black) and a difficulty setting (`AI_DEPTH`).
3. Fifty-move rule, move list panel, PGN export.
4. Split `Chess.py` into `engine.py`, `ai.py`, `ui.py`.

## Troubleshooting

- `ModuleNotFoundError: pygame` → `pip install -r requirements-desktop.txt` (desktop app only).
- Vercel build installs pygame / is slow → make sure `requirements.txt` stays free of desktop dependencies.
- `FileNotFoundError: images/wK.png` → run from the repository root.
