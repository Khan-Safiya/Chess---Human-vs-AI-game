# Chess — Human vs AI

A chess game with a **pure-Python engine** that runs two ways: as a desktop app
([pygame](https://www.pygame.org/)) and as a website hosted on [Vercel](https://vercel.com) (Python serverless
API + a thin browser page). You play **White**; a minimax AI with alpha-beta pruning plays **Black**.

## Features

- Full 8×8 board with piece images, coordinate labels and click-to-move play
- Legal-move highlighting, last-move highlight, and a red outline on a king in check
- **Complete rules:** castling, en passant, promotion (you choose queen / rook / bishop / knight),
  check, checkmate, stalemate, threefold repetition and insufficient-material draws
- **Undo** (takes back your last move and the AI's reply) and **New Game**
- Minimax AI (depth 3, alpha-beta pruning, move ordering, material evaluation) running on a background
  thread, so the window never freezes while it thinks
- Built-in Help screen
- Engine test suite verified against standard perft node counts

## Requirements

- Python 3.9+
- Desktop version only: pygame 2.5+ (`requirements-desktop.txt`). The web version uses the standard library only.

## Quick start (desktop)

```bash
git clone https://github.com/Khan-Safiya/Chess---Human-vs-AI-game.git
cd Chess---Human-vs-AI-game

python -m venv .venv
# Windows:     .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements-desktop.txt
python Chess.py
```

> Run the game **from the repository folder** — piece images are loaded from the relative path `images/`.

## Run the website locally

```bash
python dev_server.py        # http://localhost:8000  (no dependencies needed)
```

## Deploy to Vercel

1. Push this repository to GitHub.
2. On [vercel.com](https://vercel.com): **Add New → Project**, import the repo, leave all settings at their defaults
   (no framework, no build command), and click **Deploy**.
   Or with the CLI: `npm i -g vercel`, then `vercel` (preview) / `vercel --prod` from the repo root.

Vercel serves `public/` as the site and each file in `api/` as a Python serverless function
(`/api/play`, `/api/ai`). `.vercelignore` keeps desktop-only files out of the deployment.
The API is stateless: the browser sends the position with each request and Python decides legality,
check, game result and the AI's reply. Cold starts add about a second to the first request.

## How to play

| Action | How |
|---|---|
| Move | Click a white piece (legal squares light up), then click a highlighted square |
| Castle | Click your king, then the square two files toward the rook |
| En passant | Click your pawn, then the highlighted diagonal square behind the enemy pawn |
| Promote | Move a pawn to the last rank, then pick a piece in the dialog (click outside to cancel) |
| Undo | **Undo** button or `U` |
| Restart | **New Game** button or `R` |
| Rules | **Help** button |

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers the JSON API (validation, castling/promotion/mate/repetition over the wire, HTTP errors) and move generation (perft on the start position and three standard stress positions), castling
rules, en passant, promotion, mate/stalemate/insufficient-material detection and AI sanity checks.

## Known limitations

- You always play White (no colour choice).
- The AI is shallow (3 plies) with a material-only evaluation: tactically alert, positionally naive.
- No fifty-move rule, no clock, no move list / save-load.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the code is organised
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — testing, headless runs, extension ideas

## Project layout

```
engine.py           # Position, rules, minimax AI (pure Python, no dependencies)
Chess.py            # desktop pygame UI (imports engine.py)
webapi.py           # stateless JSON API logic (play / ai) + HTTP glue
api/play.py, ai.py  # Vercel serverless entry points
public/             # website: index.html + piece images
dev_server.py       # local server mirroring the Vercel layout
images/             # piece sprites for the desktop app (copy lives in public/images)
tests/              # unittest suite (perft, rules, AI, API)
docs/               # architecture and development notes
vercel.json, .vercelignore, requirements*.txt
```
