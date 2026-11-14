"""Chess - Human (White) vs AI (Black), built with pygame.

Layers: Position/rules engine -> minimax AI -> pygame UI (see docs/ARCHITECTURE.md).
"""
import math
import sys
import threading

import pygame

from engine import (AI_DEPTH, PROMOTION_CHOICES, apply_move, find_king, game_result, generate_moves,
                    init_position, is_friend, is_in_check, minimax, move_to_string)

pygame.init()

# ----------------------------------------------------------------- constants
BOARD_SIZE = 720
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 60
BUTTON_HEIGHT = 30
BOTTOM_PANEL_HEIGHT = 40

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_SQUARE = (118, 150, 86)
LIGHT_SQUARE = (238, 238, 210)
HIGHLIGHT = (186, 202, 68)
LAST_MOVE_LIGHT = (246, 246, 130)
LAST_MOVE_DARK = (186, 202, 43)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 149, 237)
CHECK_COLOR = (220, 70, 70)




def load_images():
    images = {}
    for piece in ['K', 'Q', 'R', 'B', 'N', 'P']:
        images[piece] = pygame.transform.scale(
            pygame.image.load(f"images/w{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))
        images[piece.lower()] = pygame.transform.scale(
            pygame.image.load(f"images/b{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))
    return images


# ---------------------------------------------------------------------- UI
def draw_button(screen, rect, text, font, enabled=True):
    hover = enabled and rect.collidepoint(pygame.mouse.get_pos())
    color = BUTTON_HOVER_COLOR if hover else BUTTON_COLOR
    if not enabled:
        color = (170, 170, 170)
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, BLACK, rect, 2)
    label = font.render(text, True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


# Every entry here is mirrored in public/index.html (a test checks the headings stay in sync).
HELP_RULES = [
    ("Objective:", "Checkmate your opponent's king. This happens when the king is in check and cannot escape capture."),
    ("Pieces:", ""),
    ("  Pawn:", "Moves forward one square(or two from starting). Captures diagonally. "
                "Promotes when reaching the other end."),
    ("  Knight:", "Moves in an L-shape (two squares in one direction, then one square perpendicular). "
                  "Can jump over pieces."),
    ("  Bishop:", "Moves diagonally any number of squares. Cannot jump over pieces."),
    ("  Rook:", "Moves horizontally or vertically any number of squares. Cannot jump over pieces."),
    ("  Queen:", "Combines the power of the rook and bishop. Most powerful piece."),
    ("  King:", "Moves one square in any direction. Cannot move into check."),
    ("Special Rules:", ""),
    ("  Check:", "When your king is threatened with capture. You must get out of check on your next move."),
    ("  Checkmate:", "When a king is in check and cannot escape. Game over."),
    ("  Stalemate:", "When a player has no legal moves but their king is not in check. Results in a draw."),
    ("  Draws:", "Can occur by stalemate, threefold repetition, or insufficient material."),
    ("  Castling:", "Move the king two squares toward an unmoved rook and the rook hops over it. Not allowed "
                    "if the king or that rook has already moved, if there are pieces in between, or if the king "
                    "is in check, passes through an attacked square, or lands on one."),
    ("  En passant:", "If an enemy pawn has just advanced two squares and lands beside your pawn, you may capture "
                      "it as if it had moved only one square - but only on the very next move."),
    ("  Promotion:", "A pawn reaching the far end of the board becomes a queen, rook, bishop or knight "
                     "- you choose."),
    ("In this game:", "You play as White. Click a piece to select it, then click a highlighted square to move."),
    ("", "The AI plays as Black and will respond automatically."),
    ("Controls:", "Undo (or U) takes back your last move and the AI's reply. New Game (or R) restarts."),
]

_help_cache = {}


def build_help_surface():
    """Render the whole Help text once onto a tall surface (it is scrolled, not clipped)."""
    if 'surf' in _help_cache:
        return _help_cache['surf']
    title_font = pygame.font.SysFont('Arial', 28, bold=True)
    sub_font = pygame.font.SysFont('Arial', 20, bold=True)
    text_font = pygame.font.SysFont('Arial', 16)

    def wrap(text, max_width):
        lines, cur = [], ""
        for w in text.split():
            trial = (cur + " " + w).strip()
            if text_font.size(trial)[0] <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        return lines + ([cur] if cur else [])

    # First pass: lay out the lines, so the surface can be sized exactly.
    items, y = [], 60                      # (kind, text, x, y)
    for head, content in HELP_RULES:
        if head.startswith("  "):
            indent, body = 30, head.strip() + " " + content
        elif head:
            items.append(('h', head, 20, y))
            y += 28
            indent, body = 30, content
        else:
            indent, body = 30, content
        for line in (wrap(body, BOARD_SIZE - indent - 25) if body else []):
            items.append(('t', line, indent, y))
            y += 21
        y += 4
    surf = pygame.Surface((BOARD_SIZE, y + 15))
    surf.fill(WHITE)
    title = title_font.render("Chess Rules", True, BLACK)
    surf.blit(title, (BOARD_SIZE // 2 - title.get_width() // 2, 15))
    for kind, text, x, ty in items:
        surf.blit((sub_font if kind == 'h' else text_font).render(text, True, BLACK), (x, ty))
    _help_cache['surf'] = surf
    return surf


def help_max_scroll():
    return max(0, build_help_surface().get_height() - BOARD_SIZE)


def draw_help_screen(screen, back_rect, scroll=0):
    """Draw the scrolled Help text in the board area and the Back button in the bottom panel."""
    surf = build_help_surface()
    scroll = max(0, min(scroll, help_max_scroll()))
    screen.fill(WHITE)
    screen.blit(surf, (0, 0), pygame.Rect(0, scroll, BOARD_SIZE, BOARD_SIZE))
    pygame.draw.line(screen, (200, 200, 200), (0, BOARD_SIZE), (BOARD_SIZE, BOARD_SIZE))
    hint_font = pygame.font.SysFont('Arial', 14)
    if help_max_scroll() > 0:
        hint = "Scroll: mouse wheel or arrow keys" if scroll < help_max_scroll() else "End of rules"
        screen.blit(hint_font.render(hint, True, (110, 110, 110)), (10, BOARD_SIZE + 13))
    draw_button(screen, back_rect, "Back to Game", pygame.font.SysFont('Arial', 16))


def promotion_rects():
    """Four square rects for the promotion picker, centred on the board."""
    x0 = (BOARD_SIZE - 4 * SQUARE_SIZE) // 2
    y0 = (BOARD_SIZE - SQUARE_SIZE) // 2
    return [pygame.Rect(x0 + k * SQUARE_SIZE, y0, SQUARE_SIZE, SQUARE_SIZE) for k in range(4)]


def draw_game(screen, pos, images, ui):
    """Draw the board, pieces, highlights, bottom panel and optional promotion picker."""
    valid_targets = {(m[2], m[3]) for m in ui['valid_moves']}
    check_sq = find_king(pos.board, pos.turn) if is_in_check(pos.board, pos.turn) else None
    last = ui['last_move']
    for row in range(8):
        for col in range(8):
            light = (row + col) % 2 == 0
            color = LIGHT_SQUARE if light else DARK_SQUARE
            if last and (row, col) in ((last[0], last[1]), (last[2], last[3])):
                color = LAST_MOVE_LIGHT if light else LAST_MOVE_DARK
            if ui['selected'] == (row, col):
                color = HIGHLIGHT
            if (row, col) in valid_targets:
                color = (208, 220, 178) if light else (155, 183, 125)
            rect = (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, color, rect)
            if check_sq == (row, col):
                pygame.draw.rect(screen, CHECK_COLOR, rect, 5)
            piece = pos.board[row][col]
            if piece != '.':
                screen.blit(images[piece], (col * SQUARE_SIZE, row * SQUARE_SIZE))
    font = pygame.font.SysFont('Arial', 12)
    for i in range(8):
        screen.blit(font.render(chr(97 + i), True, BLACK if i % 2 == 0 else WHITE),
                    (i * SQUARE_SIZE + 2, BOARD_SIZE - 14))
        screen.blit(font.render(str(8 - i), True, BLACK if i % 2 == 1 else WHITE), (2, i * SQUARE_SIZE + 2))

    pygame.draw.rect(screen, WHITE, (0, BOARD_SIZE, BOARD_SIZE, BOTTOM_PANEL_HEIGHT))
    msg_font = pygame.font.SysFont('Arial', 17)
    text = msg_font.render(ui['message'], True, BLACK)
    screen.blit(text, text.get_rect(midleft=(10, BOARD_SIZE + BOTTOM_PANEL_HEIGHT // 2)))
    btn_font = pygame.font.SysFont('Arial', 16)
    draw_button(screen, ui['undo_rect'], "Undo", btn_font, enabled=ui['can_undo'])
    draw_button(screen, ui['new_rect'], "New Game", btn_font)
    draw_button(screen, ui['help_rect'], "Help", btn_font)

    if ui['pending_promo']:
        overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        rects = promotion_rects()
        strip = rects[0].unionall(rects[1:])
        pygame.draw.rect(screen, WHITE, pygame.Rect(strip.x - 10, strip.y - 42, strip.w + 20, strip.h + 52))
        label = pygame.font.SysFont('Arial', 18, bold=True).render("Promote to:", True, BLACK)
        screen.blit(label, (strip.x, strip.y - 32))
        for r, p in zip(rects, PROMOTION_CHOICES):
            hovered = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, LIGHT_SQUARE if hovered else (200, 200, 180), r)
            screen.blit(images[p], r.topleft)


def ai_worker(pos, out):
    """Run the search off the UI thread; the result is left in `out`."""
    _, move = minimax(pos, AI_DEPTH, -math.inf, math.inf)
    out['move'] = move
    out['done'] = True


def main():
    screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE + BOTTOM_PANEL_HEIGHT))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()
    images = load_images()

    panel_y = BOARD_SIZE + (BOTTOM_PANEL_HEIGHT - BUTTON_HEIGHT) // 2
    help_rect = pygame.Rect(BOARD_SIZE - 80, panel_y, 70, BUTTON_HEIGHT)
    new_rect = pygame.Rect(help_rect.x - 100, panel_y, 90, BUTTON_HEIGHT)
    undo_rect = pygame.Rect(new_rect.x - 80, panel_y, 70, BUTTON_HEIGHT)
    back_rect = pygame.Rect(BOARD_SIZE // 2 - 80, panel_y, 160, BUTTON_HEIGHT)

    S = {}   # mutable game state

    def status(pos):
        if pos.turn == 'white':
            return "Check! Your move." if is_in_check(pos.board, 'white') else "Your turn (White)"
        return "AI is thinking..."

    def new_game():
        S.update(pos=init_position(), selected=None, valid_moves=[], pending_promo=[], last_move=None,
                 over=False, undo_stack=[], ai=None)
        S['history'] = {S['pos'].key(): 1}
        S['message'] = status(S['pos'])

    def play(move, by_human):
        if by_human:
            S['undo_stack'].append((S['pos'], dict(S['history']), S['last_move']))
        S['pos'] = apply_move(S['pos'], move)
        S['last_move'] = move
        key = S['pos'].key()
        S['history'][key] = S['history'].get(key, 0) + 1
        result = game_result(S['pos'], S['history'])
        if result:
            S['over'], S['message'] = True, result
        elif by_human:
            S['message'] = status(S['pos'])
        else:
            check = " - Check!" if is_in_check(S['pos'].board, 'white') else ""
            S['message'] = f"AI moved: {move_to_string(move)}{check}"
        S['selected'], S['valid_moves'], S['pending_promo'] = None, [], []

    def undo():
        if not S['undo_stack']:
            return
        S['pos'], S['history'], S['last_move'] = S['undo_stack'].pop()
        # ai=None also orphans any search still running; its result is simply discarded.
        S.update(over=False, ai=None, selected=None, valid_moves=[], pending_promo=[])
        S['message'] = "Move undone. " + status(S['pos'])

    def select(row, col):
        if is_friend(S['pos'].board[row][col], 'white'):
            S['selected'] = (row, col)
            S['valid_moves'] = [m for m in generate_moves(S['pos']) if m[0] == row and m[1] == col]
        else:
            S['selected'], S['valid_moves'] = None, []

    def board_click(mouse):
        if S['pending_promo']:
            for r, p in zip(promotion_rects(), PROMOTION_CHOICES):
                if r.collidepoint(mouse):
                    play(next(m for m in S['pending_promo'] if m[4] == p), True)
                    return
            S['pending_promo'], S['selected'], S['valid_moves'] = [], None, []   # click outside cancels
            return
        col, row = mouse[0] // SQUARE_SIZE, mouse[1] // SQUARE_SIZE
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        if S['selected'] is None:
            select(row, col)
            return
        matches = [m for m in S['valid_moves'] if m[2] == row and m[3] == col]
        if len(matches) > 1:                    # promotion: ask which piece
            S['pending_promo'] = matches
        elif matches:
            play(matches[0], True)
        else:
            select(row, col)

    new_game()
    is_help = False
    help_scroll = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and is_help:
                step = {pygame.K_UP: -40, pygame.K_DOWN: 40, pygame.K_PAGEUP: -400, pygame.K_PAGEDOWN: 400}
                if event.key in step:
                    help_scroll = max(0, min(help_scroll + step[event.key], help_max_scroll()))
                elif event.key == pygame.K_ESCAPE:
                    is_help = False
            elif event.type == pygame.MOUSEWHEEL and is_help:
                help_scroll = max(0, min(help_scroll - event.y * 40, help_max_scroll()))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_u:
                    undo()
                elif event.key == pygame.K_r:
                    new_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_help:
                    if back_rect.collidepoint(event.pos):
                        is_help = False
                elif help_rect.collidepoint(event.pos):
                    is_help, help_scroll = True, 0
                elif new_rect.collidepoint(event.pos):
                    new_game()
                elif undo_rect.collidepoint(event.pos):
                    undo()
                elif S['pos'].turn == 'white' and not S['over']:
                    board_click(event.pos)

        # AI: start a background search when it is Black's turn, apply the result when ready.
        if S['pos'].turn == 'black' and not S['over']:
            if S['ai'] is None:
                S['ai'] = {'done': False, 'move': None}
                threading.Thread(target=ai_worker, args=(S['pos'], S['ai']), daemon=True).start()
            elif S['ai']['done']:
                move, S['ai'] = S['ai']['move'], None
                if move:
                    play(move, False)

        if is_help:
            draw_help_screen(screen, back_rect, help_scroll)
        else:
            screen.fill(WHITE)
            draw_game(screen, S['pos'], images, dict(
                selected=S['selected'], valid_moves=S['valid_moves'], message=S['message'],
                last_move=S['last_move'], pending_promo=S['pending_promo'], can_undo=bool(S['undo_stack']),
                undo_rect=undo_rect, new_rect=new_rect, help_rect=help_rect))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
