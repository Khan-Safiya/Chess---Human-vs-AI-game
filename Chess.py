import math
import copy
import pygame
import sys

# Initialize pygame
pygame.init()

# Constants
BOARD_SIZE = 720
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 60
HELP_BUTTON_HEIGHT = 30
BOTTOM_PANEL_HEIGHT = 40

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_SQUARE = (118, 150, 86)
LIGHT_SQUARE = (238, 238, 210)
HIGHLIGHT = (186, 202, 68)
MOVE_HIGHLIGHT = (214, 214, 189)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 149, 237)

def load_images():
    images = {}
    pieces = ['K', 'Q', 'R', 'B', 'N', 'P']
    for piece in pieces:
        images[piece] = pygame.transform.scale(
            pygame.image.load(f"images/w{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))
        images[piece.lower()] = pygame.transform.scale(
            pygame.image.load(f"images/b{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))
    return images

def init_board():
    board = [
        list("rnbqkbnr"), 
        list("pppppppp"),
        list("........"),
        list("........"),
        list("........"),
        list("........"),
        list("PPPPPPPP"),
        list("RNBQKBNR")
    ]
    return board

def is_inside(row, col):
    return 0<=row<8 and 0<=col<8

def is_enemy(piece, color):
    if piece == '.':
        return False
    if color == 'white':
        return piece.islower()
    else:
        return piece.isupper()

def is_friend(piece, color):
    if piece == '.':
        return False
    if color == 'white':
        return piece.isupper()
    else:
        return piece.islower()

def board_to_string(board):
    # Convert the board to a string representation for comparing positions
    result = ""
    for row in board:
        result += ''.join(row)
    return result

def simulate_move(board, move):
    # Return a new board resulting from applying the move. A move is a tuple: (from_row, from_col, to_row, to_col, promotion)
    # The promotion field (if not None) should be the piece that the pawn promotes to.
    new_board = copy.deepcopy(board)
    fr, fc, tr, tc, promo = move
    piece = new_board[fr][fc]
    new_board[fr][fc] = '.'
    if promo:
        new_board[tr][tc] = promo
    else:
        new_board[tr][tc] = piece
    return new_board

def find_king(board, color):
    king_char = 'K' if color == 'white' else 'k'
    for i in range(8):
        for j in range(8):
            if board[i][j] == king_char:
                return (i, j)
    return None

def is_square_attacked(board, row, col, attacker_color):
    # Return True if the square (row, col) is attacked by any piece of attacker_color.
    # Checks pawn, knight, sliding pieces, and king attacks.
    # Directions for king (and later for sliding moves)

    directions = [(-1, -1), (-1, 0), (-1, 1),
                  (0, -1),          (0, 1),
                  (1, -1),  (1, 0),  (1, 1)]
    
    # Pawn attack directions (they attack diagonally)
    if attacker_color == 'white':
        pawn_dirs = [(-1, -1), (-1, 1)]
    else:
        pawn_dirs = [(1, -1), (1, 1)]
    for dr, dc in pawn_dirs:
        r = row + dr
        c = col + dc
        if is_inside(r, c):
            p = board[r][c]
            if attacker_color == 'white' and p == 'P':
                return True
            if attacker_color == 'black' and p == 'p':
                return True
    
    # Knight moves
    knight_moves = [(2, 1), (1, 2), (-1, 2), (-2, 1),
                    (-2, -1), (-1, -2), (1, -2), (2, -1)]
    for dr, dc in knight_moves:
        r = row + dr
        c = col + dc
        if is_inside(r, c):
            p = board[r][c]
            if attacker_color == 'white' and p == 'N':
                return True
            if attacker_color == 'black' and p == 'n':
                return True

    # Sliding pieces: rook and queen (horizontal/vertical)
    rook_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for dr, dc in rook_dirs:
        r, c = row, col
        while True:
            r += dr
            c += dc
            if not is_inside(r, c):
                break
            if board[r][c] != '.':
                p = board[r][c]
                if attacker_color == 'white' and p in ('R', 'Q'):
                    return True
                if attacker_color == 'black' and p in ('r', 'q'):
                    return True
                break
    # Sliding pieces: bishop and queen (diagonals)
    bishop_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in bishop_dirs:
        r, c = row, col
        while True:
            r += dr
            c += dc
            if not is_inside(r, c):
                break
            if board[r][c] != '.':
                p = board[r][c]
                if attacker_color == 'white' and p in ('B', 'Q'):
                    return True
                if attacker_color == 'black' and p in ('b', 'q'):
                    return True
                break

    # King (adjacent squares)
    for dr, dc in directions:
        r = row + dr
        c = col + dc
        if is_inside(r, c):
            p = board[r][c]
            if attacker_color == 'white' and p == 'K':
                return True
            if attacker_color == 'black' and p == 'k':
                return True

    return False

def is_in_check(board, color):
    # Returns True if the king of the given color is in check.
    king_pos = find_king(board, color)
    if not king_pos:
        return True
    king_row, king_col = king_pos
    enemy_color = 'black' if color == 'white' else 'white'
    return is_square_attacked(board, king_row, king_col, enemy_color)

def generate_moves(board, color):
    # Generate all *legal* moves for the given color.
    # A move is represented as a tuple: (from_row, from_col, to_row, to_col, promotion)
    # where promotion is either None or (for simplicity) a Queen.
    moves = []
    for i in range(8):
        for j in range(8):
            piece = board[i][j]
            if piece == '.':
                continue
            if color == 'white' and piece.isupper():
                moves.extend(generate_piece_moves(board, i, j, color))
            elif color == 'black' and piece.islower():
                moves.extend(generate_piece_moves(board, i, j, color))
    # Filter out moves that leave the king in check
    legal_moves = []
    for move in moves:
        new_board = simulate_move(board, move)
        if not is_in_check(new_board, color):
            legal_moves.append(move)
    return legal_moves

def generate_piece_moves(board, i, j, color):
    # Generate pseudo-legal moves (without king safety check) for the piece at (i,j).
    piece = board[i][j]
    moves = []
    piece_type = piece.upper()
    if piece_type == 'P':
        moves.extend(generate_pawn_moves(board, i, j, color))
    elif piece_type == 'N':
        moves.extend(generate_knight_moves(board, i, j, color))
    elif piece_type == 'B':
        moves.extend(generate_sliding_moves(board, i, j, color, [(-1,-1), (-1,1), (1,-1), (1,1)]))
    elif piece_type == 'R':
        moves.extend(generate_sliding_moves(board, i, j, color, [(-1,0), (1,0), (0,-1), (0,1)]))
    elif piece_type == 'Q':
        moves.extend(generate_sliding_moves(board, i, j, color,
                                             [(-1,-1), (-1,1), (1,-1), (1,1),
                                              (-1,0), (1,0), (0,-1), (0,1)]))
    elif piece_type == 'K':
        moves.extend(generate_king_moves(board, i, j, color))
    return moves

def generate_pawn_moves(board, i, j, color):
    moves = []
    if color == 'white':
        direction = -1
        start_row = 6
        promotion_row = 0
    else:
        direction = 1
        start_row = 1
        promotion_row = 7
    new_i = i + direction
    # One square forward
    if is_inside(new_i, j) and board[new_i][j] == '.':
        if new_i == promotion_row:
            moves.append((i, j, new_i, j, 'Q' if color=='white' else 'q'))
        else:
            moves.append((i, j, new_i, j, None))
        # Two squares forward from starting row
        if i == start_row:
            new_i2 = i + 2 * direction
            if is_inside(new_i2, j) and board[new_i2][j] == '.':
                moves.append((i, j, new_i2, j, None))
    # Captures
    for dj in [-1, 1]:
        new_j = j + dj
        if is_inside(new_i, new_j) and board[new_i][new_j] != '.' and is_enemy(board[new_i][new_j], color):
            if new_i == promotion_row:
                moves.append((i, j, new_i, new_j, 'Q' if color=='white' else 'q'))
            else:
                moves.append((i, j, new_i, new_j, None))
    return moves

def generate_knight_moves(board, i, j, color):
    moves = []
    knight_moves = [(2,1), (1,2), (-1,2), (-2,1),
                    (-2,-1), (-1,-2), (1,-2), (2,-1)]
    for dr, dc in knight_moves:
        new_i = i + dr
        new_j = j + dc
        if is_inside(new_i, new_j):
            target = board[new_i][new_j]
            if target == '.' or is_enemy(target, color):
                moves.append((i, j, new_i, new_j, None))
    return moves

def generate_sliding_moves(board, i, j, color, directions):
    moves = []
    for dr, dc in directions:
        new_i = i + dr
        new_j = j + dc
        while is_inside(new_i, new_j):
            target = board[new_i][new_j]
            if target == '.':
                moves.append((i, j, new_i, new_j, None))
            elif is_enemy(target, color):
                moves.append((i, j, new_i, new_j, None))
                break
            else:
                break
            new_i += dr
            new_j += dc
    return moves

def generate_king_moves(board, i, j, color):
    moves = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            new_i = i + dr
            new_j = j + dc
            if is_inside(new_i, new_j):
                target = board[new_i][new_j]
                if target == '.' or is_enemy(target, color):
                    moves.append((i, j, new_i, new_j, None))
    return moves

def evaluate_board(board):
    # A simple material-based evaluation.
    # Positive scores favor White; negative scores favor Black.

    values = {
        'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0
    }
    score = 0
    for row in board:
        for piece in row:
            if piece == '.':
                continue
            if piece.isupper():
                score += values.get(piece, 0)
            else:
                score -= values.get(piece.upper(), 0)
    return score

def game_over(board, turn):
    return len(generate_moves(board, turn)) == 0

def minimax(board, turn, depth, alpha, beta):
    # A minimax search with alpha–beta pruning.
    # Since our evaluation is (white – black), White seeks to maximize while Black seeks to minimize.
    # (User is White; AI is Black.)

    if depth == 0 or game_over(board, turn):
        return evaluate_board(board), None
    legal_moves = generate_moves(board, turn)
    if turn == 'white':
        max_eval = -math.inf
        best_move = None
        for move in legal_moves:
            new_board = simulate_move(board, move)
            next_turn = 'black'
            eval_score, _ = minimax(new_board, next_turn, depth - 1, alpha, beta)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:  # Black's turn (AI) minimizes the score.
        min_eval = math.inf
        best_move = None
        for move in legal_moves:
            new_board = simulate_move(board, move)
            next_turn = 'white'
            eval_score, _ = minimax(new_board, next_turn, depth - 1, alpha, beta)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move

def move_to_string(move):
    # Convert a move tuple back to a string (e.g., 'e2e4' or 'e7e8Q').
    files = 'abcdefgh'
    fr, fc, tr, tc, promo = move
    s = files[fc] + str(8 - fr) + files[tc] + str(8 - tr)
    if promo:
        s += promo.upper()
    return s

def parse_move(from_square, to_square):
    # Parse a move from GUI coordinates into a move tuple:
    #   (from_row, from_col, to_row, to_col, promotion)
    # For simplicity the promotion field is left as None (our move generator automatically adds a Queen promotion when needed).

    from_row, from_col = from_square
    to_row, to_col = to_square
    return (from_row, from_col, to_row, to_col, None)

def draw_button(screen, rect, text, font, color, hover_color=None):
    # Draw a button with text
    mouse_pos = pygame.mouse.get_pos()
    if hover_color and rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, hover_color, rect)
    else:
        pygame.draw.rect(screen, color, rect)
    
    pygame.draw.rect(screen, BLACK, rect, 2)  # Button border
    
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    
    return rect.collidepoint(mouse_pos)

def draw_help_screen(screen, font, back_button_rect):
    # Draw the help screen with chess rules
    screen.fill(WHITE)
    
    title_font = pygame.font.SysFont('Arial', 28, bold=True)
    subtitle_font = pygame.font.SysFont('Arial', 20, bold=True)
    text_font = pygame.font.SysFont('Arial', 16)
    
    # Title
    title = title_font.render("Chess Rules", True, BLACK)
    screen.blit(title, (BOARD_SIZE // 2 - title.get_width() // 2, 20))
    
    # Rules content
    rules = [
        ("Objective:", "Checkmate your opponent's king. This happens when the king is in check and cannot escape capture."),
        ("Pieces:", ""),
        ("  Pawn:", "Moves forward one square(or two from starting). Captures diagonally. Promotes when reaching the other end."),
        ("  Knight:", "Moves in an L-shape (two squares in one direction, then one square perpendicular). Can jump over pieces."),
        ("  Bishop:", "Moves diagonally any number of squares. Cannot jump over pieces."),
        ("  Rook:", "Moves horizontally or vertically any number of squares. Cannot jump over pieces."),
        ("  Queen:", "Combines the power of the rook and bishop. Most powerful piece."),
        ("  King:", "Moves one square in any direction. Cannot move into check."),
        ("Special Rules:", ""),
        ("  Check:", "When your king is threatened with capture. You must get out of check on your next move."),
        ("  Checkmate:", "When a king is in check and cannot escape. Game over."),
        ("  Stalemate:", "When a player has no legal moves but their king is not in check. Results in a draw."),
        ("  Draws:", "Can occur by stalemate, threefold repetition, or insufficient material."),
        ("In this game:", "You play as White. Click a piece to select it, then click a highlighted square to move."),
        ("", "The AI plays as Black and will respond automatically.")
    ]
    
    y_pos = 70
    for title, content in rules:
        if title.startswith("  "):  # It's a subpoint
            x_pos = 30
        else:
            x_pos = 20
            if title and ":" in title:  # It's a section title
                section = subtitle_font.render(title, True, BLACK)
                screen.blit(section, (x_pos, y_pos))
                y_pos += 30
                continue
        
        # Render the line
        if title:
            line = text_font.render(title + " " + content, True, BLACK)
        else:
            line = text_font.render(content, True, BLACK)
        
        screen.blit(line, (x_pos, y_pos))
        y_pos += 25
    
    # Back button
    is_hover = draw_button(screen, back_button_rect, "Back to Game", font, BUTTON_COLOR, BUTTON_HOVER_COLOR)
    
    return is_hover

def draw_board(screen, board, piece_images, selected=None, valid_moves=None, message=None, help_button_rect=None, is_help_screen=False):
    if is_help_screen:
        return draw_help_screen(screen, pygame.font.SysFont('Arial', 18), help_button_rect)
    
    for row in range(8):
        for col in range(8):
            # Determine square color
            if (row + col) % 2 == 0:
                color = LIGHT_SQUARE
            else:
                color = DARK_SQUARE
                
            # Highlight selected square
            if selected and selected[0] == row and selected[1] == col:
                color = HIGHLIGHT
                
            # Highlight valid move squares
            if valid_moves and (row, col) in [(m[2], m[3]) for m in valid_moves]:
                if (row + col) % 2 == 0:
                    color = (208, 220, 178)  # Lighter highlight for light squares
                else:
                    color = (155, 183, 125)  # Darker highlight for dark squares
                
            # Draw square
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
            
            # Draw pieces
            piece = board[row][col]
            if piece != '.':
                screen.blit(piece_images[piece], (col * SQUARE_SIZE, row * SQUARE_SIZE))
    
    # Draw coordinate labels (a-h, 1-8)
    font = pygame.font.SysFont('Arial', 12)
    for i in range(8):
        # File labels (a-h)
        label = font.render(chr(97 + i), True, BLACK if i % 2 == 0 else WHITE)
        screen.blit(label, (i * SQUARE_SIZE + 2, BOARD_SIZE - 12))
        
        # Rank labels (1-8)
        label = font.render(str(8 - i), True, BLACK if i % 2 == 1 else WHITE)
        screen.blit(label, (2, i * SQUARE_SIZE + 2))
    
    # Draw bottom panel with message
    pygame.draw.rect(screen, WHITE, (0, BOARD_SIZE, BOARD_SIZE, BOTTOM_PANEL_HEIGHT))
    
    # Draw message if there is one
    if message:
        font = pygame.font.SysFont('Arial', 18)
        text = font.render(message, True, BLACK)
        text_rect = text.get_rect(center=(BOARD_SIZE // 2, BOARD_SIZE + BOTTOM_PANEL_HEIGHT // 2))
        screen.blit(text, text_rect)
    
    # Draw help button
    help_font = pygame.font.SysFont('Arial', 16)
    is_hover = draw_button(screen, help_button_rect, "Help", help_font, BUTTON_COLOR, BUTTON_HOVER_COLOR)
    
    return is_hover

def main():
    # Setup pygame window
    window_height = BOARD_SIZE + BOTTOM_PANEL_HEIGHT
    screen = pygame.display.set_mode((BOARD_SIZE, window_height))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()
    
    # Load piece images
    piece_images = load_images()
    
    # Initialize board and game state
    board = init_board()
    turn = 'white'  # User plays White; AI plays Black.
    selected = None
    valid_moves = []
    game_message = "Your turn (White)"
    game_over_flag = False
    is_help_screen = False
    
    # Help button
    help_button_rect = pygame.Rect(BOARD_SIZE - 80, BOARD_SIZE + 5, 70, HELP_BUTTON_HEIGHT)
    back_button_rect = pygame.Rect(BOARD_SIZE // 2 - 80, BOARD_SIZE - 40, 160, 30)
    
    # Add position history to detect repetition
    position_history = {}
    # Store both the position and whose turn it is, since repetition requires the same player to move
    position_history[(board_to_string(board), turn)] = 1
    
    # Main game loop
    running = True
    while running:
        button_hover = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                # Check if help button was clicked
                if help_button_rect.collidepoint(mouse_pos) and not is_help_screen:
                    is_help_screen = True
                    continue
                
                # Check if back button was clicked in help screen
                if is_help_screen and back_button_rect.collidepoint(mouse_pos):
                    is_help_screen = False
                    continue
                
                # If in help screen, ignore other clicks
                if is_help_screen:
                    continue
                
                # If it's player's turn, handle board clicks
                if turn == 'white':
                    # Convert to board coordinates
                    col = mouse_pos[0] // SQUARE_SIZE
                    row = mouse_pos[1] // SQUARE_SIZE
                    
                    # Check if click is within the board
                    if 0 <= row < 8 and 0 <= col < 8:
                        # If no piece is selected, select it if it's the player's piece
                        if selected is None:
                            piece = board[row][col]
                            if is_friend(piece, 'white'):
                                selected = (row, col)
                                # Get valid moves for the selected piece
                                all_moves = generate_moves(board, 'white')
                                valid_moves = [m for m in all_moves if m[0] == row and m[1] == col]
                        else:
                            # If a piece is already selected
                            # Try to make a move
                            move = None
                            for m in valid_moves:
                                if m[2] == row and m[3] == col:
                                    move = m
                                    break
                            
                            if move:
                                # Make the move
                                board = simulate_move(board, move)
                                selected = None
                                valid_moves = []
                                turn = 'black'
                                game_message = "AI is thinking..."
                                
                                # Check for threefold repetition after the player's move
                                position_key = (board_to_string(board), turn)
                                position_history[position_key] = position_history.get(position_key, 0) + 1
                                
                                if position_history[position_key] >= 3:
                                    game_message = "Draw by threefold repetition!"
                                    game_over_flag = True
                                # Check for game over
                                elif game_over(board, 'black'):
                                    if is_in_check(board, 'black'):
                                        game_message = "Checkmate! White wins."
                                    else:
                                        game_message = "Stalemate!"
                                    game_over_flag = True
                            else:
                                # Select a different piece or deselect
                                piece = board[row][col]
                                if is_friend(piece, 'white'):
                                    selected = (row, col)
                                    all_moves = generate_moves(board, 'white')
                                    valid_moves = [m for m in all_moves if m[0] == row and m[1] == col]
                                else:
                                    selected = None
                                    valid_moves = []
        
        # AI's turn (Black)
        if turn == 'black' and running and not game_over_flag and not is_help_screen:
            # AI thinks and makes a move
            _, ai_move = minimax(board, 'black', depth=3, alpha=-math.inf, beta=math.inf)
            
            if ai_move:
                # Make the AI's move
                board = simulate_move(board, ai_move)
                game_message = f"AI moved: {move_to_string(ai_move)}"
                turn = 'white'
                
                # Check for threefold repetition after the AI's move
                position_key = (board_to_string(board), turn)
                position_history[position_key] = position_history.get(position_key, 0) + 1
                
                if position_history[position_key] >= 3:
                    game_message = "Draw by threefold repetition!"
                    game_over_flag = True
                # Check for game over
                elif game_over(board, 'white'):
                    if is_in_check(board, 'white'):
                        game_message = "Checkmate! Black wins."
                    else:
                        game_message = "Stalemate!"
                    game_over_flag = True
            else:
                if is_in_check(board, 'black'):
                    game_message = "Checkmate! White wins."
                else:
                    game_message = "Stalemate!"
                game_over_flag = True
        
        # Draw the game state
        screen.fill(WHITE)
        button_rect = help_button_rect
        if is_help_screen:
            button_rect = back_button_rect
        
        button_hover = draw_board(screen, board, piece_images, selected, valid_moves, game_message, button_rect, is_help_screen)
        
        pygame.display.flip()
        clock.tick(FPS)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()