## test.py
import pygame
import tkinter as tk
from tkinter import messagebox
import os
import random
import numpy as np # For sound generation

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600 # Total window height
GAME_AREA_HEIGHT = 550 # Height of the playable game area
SCORE_AREA_HEIGHT = SCREEN_HEIGHT - GAME_AREA_HEIGHT # Space for score/lives text

PADDLE_WIDTH = 120 
PADDLE_HEIGHT = 20
PADDLE_COLOR = (200, 200, 200) # Light grey

BALL_RADIUS = 7 # Using radius for drawing, rect for collision
BALL_COLOR = (255, 255, 0) # Yellow
BALL_SPEED_INITIAL_X = 4.0 # Float for more precise calculations
BALL_SPEED_INITIAL_Y = -4.0 # Float
BALL_MAX_SPEED_X_FACTOR = 1.5 # Factor of initial speed for paddle deflection

BRICK_WIDTH = 75
BRICK_HEIGHT = 20
BRICK_COLORS = [(255, 0, 0), (255, 120, 0), (255,255,0), (0, 255, 0), (0, 0, 255), (128,0,128)] # Red, Orange, Yellow, Green, Blue, Purple
BRICK_ROWS = 5
BRICK_COLS_COUNT = 8 # Number of bricks per row
BRICK_TOP_OFFSET = 50
BRICK_PADDING = 5

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)

# --- Global Variables ---
score = 0
lives = 3
game_font = None
paddle = None
ball_rect = None # Pygame Rect for ball's collision
ball_dx = 0.0 # Float for precision
ball_dy = 0.0 # Float for precision
bricks = [] # List of dictionaries: {'rect': pygame.Rect, 'color': tuple, 'alive': bool}

game_over_flag = False
game_paused = False 
game_started = False # True when ball is launched

pygame_screen = None 
root_tk = None 

# Sound objects
beep_brick = None
beep_paddle = None
beep_wall = None
beep_lose_life = None

# --- Sound Generation ---
def generate_beep_sound(frequency=440, duration=0.1, vol=0.3):
    if not pygame.mixer.get_init(): # Ensure mixer is initialized
        return None
    sample_rate = pygame.mixer.get_init()[0] 
    if sample_rate == 0: # Mixer not properly initialized
        print("Warning: Sound mixer sample rate is 0. Cannot generate sound.")
        return None
    n_samples = int(round(duration * sample_rate))
    sound_buffer = np.zeros((n_samples, 2), dtype=np.int16) # Stereo
    max_amplitude = int(vol * (2**15 -1)) 

    for i in range(n_samples):
        t = float(i) / sample_rate
        value = int(max_amplitude * np.sin(2 * np.pi * frequency * t))
        sound_buffer[i][0] = value 
        sound_buffer[i][1] = value 
    
    sound = pygame.sndarray.make_sound(sound_buffer)
    return sound

# --- Game Functions ---
def init_game_elements():
    global paddle, ball_rect, bricks, score 
    global game_over_flag, game_started

    paddle_y = GAME_AREA_HEIGHT - PADDLE_HEIGHT - 10
    paddle = pygame.Rect((SCREEN_WIDTH - PADDLE_WIDTH) // 2, paddle_y, PADDLE_WIDTH, PADDLE_HEIGHT)

    ball_size = BALL_RADIUS * 2
    ball_rect = pygame.Rect(paddle.centerx - BALL_RADIUS, paddle.top - ball_size - 2, ball_size, ball_size)

    bricks = []
    total_bricks_width = BRICK_COLS_COUNT * BRICK_WIDTH + (BRICK_COLS_COUNT - 1) * BRICK_PADDING
    start_x_bricks = (SCREEN_WIDTH - total_bricks_width) // 2

    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS_COUNT):
            brick_x = start_x_bricks + c * (BRICK_WIDTH + BRICK_PADDING)
            brick_y = BRICK_TOP_OFFSET + r * (BRICK_HEIGHT + BRICK_PADDING)
            color = BRICK_COLORS[r % len(BRICK_COLORS)]
            b_rect = pygame.Rect(brick_x, brick_y, BRICK_WIDTH, BRICK_HEIGHT)
            bricks.append({'rect': b_rect, 'color': color, 'alive': True})
    
    score = 0 # Score is reset here too, as it's part of init
    game_over_flag = False
    game_started = False 

def reset_ball_on_paddle():
    global ball_rect, ball_dx, ball_dy, game_started
    ball_size = BALL_RADIUS * 2
    ball_rect.centerx = paddle.centerx
    ball_rect.bottom = paddle.top - 2
    ball_dx = 0.0
    ball_dy = 0.0
    game_started = False

def launch_ball():
    global ball_dx, ball_dy, game_started
    if not game_started:
        ball_dx = random.choice([-BALL_SPEED_INITIAL_X, BALL_SPEED_INITIAL_X]) 
        ball_dy = BALL_SPEED_INITIAL_Y
        game_started = True

def move_ball_and_collide():
    global ball_rect, ball_dx, ball_dy, score, lives, game_over_flag

    if not game_started:
        ball_rect.centerx = paddle.centerx
        ball_rect.bottom = paddle.top - 2
        return

    ball_rect.x += ball_dx
    ball_rect.y += ball_dy

    # Wall collisions
    if ball_rect.left <= 0:
        ball_rect.left = 0
        ball_dx *= -1
        if beep_wall: beep_wall.play()
    elif ball_rect.right >= SCREEN_WIDTH:
        ball_rect.right = SCREEN_WIDTH
        ball_dx *= -1
        if beep_wall: beep_wall.play()
    
    if ball_rect.top <= 0:
        ball_rect.top = 0
        ball_dy *= -1
        if beep_wall: beep_wall.play()

    # Paddle collision
    if ball_rect.colliderect(paddle) and ball_dy > 0: 
        ball_rect.bottom = paddle.top 
        ball_dy *= -1
        
        hit_offset = ball_rect.centerx - paddle.centerx
        normalized_offset = hit_offset / (PADDLE_WIDTH / 2.0)
        
        new_ball_dx = normalized_offset * (abs(BALL_SPEED_INITIAL_X) * BALL_MAX_SPEED_X_FACTOR)
        
        max_abs_dx = abs(BALL_SPEED_INITIAL_X) * BALL_MAX_SPEED_X_FACTOR
        ball_dx = max(-max_abs_dx, min(max_abs_dx, new_ball_dx))

        # Ensure minimum horizontal speed if it's not meant to be zero (e.g. center hit)
        if abs(ball_dx) < 0.5 and normalized_offset != 0 : # if it wasn't a perfect center hit
             ball_dx = 0.5 if ball_dx >=0 else -0.5
        elif abs(ball_dx) < 0.1 and normalized_offset == 0: # perfect center hit, very slow horizontal
            ball_dx = random.choice([-0.5, 0.5]) # Give it a tiny nudge

        if beep_paddle: beep_paddle.play()

    # Brick collisions
    for brick_item in bricks:
        if brick_item['alive'] and ball_rect.colliderect(brick_item['rect']):
            brick_item['alive'] = False
            score += 10
            if beep_brick: beep_brick.play()

            overlap_left = ball_rect.right - brick_item['rect'].left
            overlap_right = brick_item['rect'].right - ball_rect.left
            overlap_top = ball_rect.bottom - brick_item['rect'].top
            overlap_bottom = brick_item['rect'].bottom - ball_rect.top

            min_overlap_x = min(overlap_left, overlap_right)
            min_overlap_y = min(overlap_top, overlap_bottom)

            if min_overlap_x < min_overlap_y: 
                ball_dx *= -1
                if overlap_left < overlap_right: ball_rect.right = brick_item['rect'].left
                else: ball_rect.left = brick_item['rect'].right
            else: 
                ball_dy *= -1
                if overlap_top < overlap_bottom: ball_rect.bottom = brick_item['rect'].top
                else: ball_rect.top = brick_item['rect'].bottom
            break 

    if all(not b['alive'] for b in bricks):
        game_over_flag = True
        return 

    if ball_rect.top >= GAME_AREA_HEIGHT:
        lives -= 1
        if beep_lose_life: beep_lose_life.play()
        if lives <= 0:
            game_over_flag = True
        else:
            reset_ball_on_paddle()

def draw_game_elements(surface):
    surface.fill(BLACK) 
    pygame.draw.rect(surface, PADDLE_COLOR, paddle)
    pygame.draw.ellipse(surface, BALL_COLOR, ball_rect)

    for brick_item in bricks:
        if brick_item['alive']:
            pygame.draw.rect(surface, brick_item['color'], brick_item['rect'])
            pygame.draw.rect(surface, GREY, brick_item['rect'], 1) 

    score_text = game_font.render(f"Score: {score}", True, WHITE)
    lives_text = game_font.render(f"Lives: {lives}", True, WHITE)
    surface.blit(score_text, (10, GAME_AREA_HEIGHT + (SCORE_AREA_HEIGHT - game_font.get_height()) // 2))
    surface.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, GAME_AREA_HEIGHT + (SCORE_AREA_HEIGHT - game_font.get_height()) // 2))

    if not game_started and not game_over_flag and lives > 0:
        launch_msg = game_font.render("Click to Launch Ball", True, WHITE)
        msg_rect = launch_msg.get_rect(center=(SCREEN_WIDTH // 2, GAME_AREA_HEIGHT // 2 + BRICK_TOP_OFFSET)) # Lower message
        surface.blit(launch_msg, msg_rect)

    pygame.display.flip()


def start_new_full_game():
    global lives, score, game_over_flag
    lives = 3
    # score = 0 # Score is reset in init_game_elements which is called next
    game_over_flag = False
    init_game_elements() 
    reset_ball_on_paddle() 

def show_end_game_message():
    global root_tk, game_over_flag # game_over_flag needs to be modifiable
    
    active_bricks = sum(1 for b in bricks if b['alive'])
    if lives <= 0:
        title = "Game Over!"
        message = f"GAME OVER! Your score: {score}."
    elif active_bricks == 0:
        title = "You Win!"
        message = f"YOU WIN! All bricks cleared! Score: {score}."
    else: 
        title = "Game Ended"
        message = f"Game ended unexpectedly. Score: {score}."

    full_message = message + "\n\nDo you want to play again?"
    
    play_again = messagebox.askyesno(title, full_message, parent=root_tk)

    if play_again:
        start_new_full_game() # This resets game_over_flag to False internally
    else:
        pygame.quit()
        if root_tk: root_tk.quit()


def game_loop_tk():
    global game_over_flag, game_paused, pygame_screen, root_tk

    if not root_tk or not root_tk.winfo_exists(): # Check if Tkinter window is still valid
        return

    if game_paused: 
        root_tk.after(50, game_loop_tk)
        return

    if game_over_flag:
        show_end_game_message() 
        # After show_end_game_message, if user chose to play again, 
        # game_over_flag is False. If they quit, root_tk might not exist.
        if root_tk and root_tk.winfo_exists(): # Check again before scheduling next frame
             root_tk.after(16, game_loop_tk)
        return

    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            on_tk_close() # Go through the Tkinter close handler
            return
        if event.type == pygame.MOUSEMOTION:
            mouse_x = event.pos[0]
            paddle.centerx = mouse_x
            if paddle.left < 0: paddle.left = 0
            if paddle.right > SCREEN_WIDTH: paddle.right = SCREEN_WIDTH
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                if not game_started and not game_over_flag and lives > 0:
                    launch_ball()

    if not game_over_flag: # Check again, as it might have changed in show_end_game_message via restart
        move_ball_and_collide()
        draw_game_elements(pygame_screen)

    if root_tk and root_tk.winfo_exists():
        root_tk.after(16, game_loop_tk) 

def on_tk_close():
    global root_tk
    # Ask confirmation only if game is not over, or if it is over but still running
    # If pygame already quit (e.g. from show_end_game_message), don't ask again.
    try:
        if pygame.display.get_init(): # Check if Pygame display is still active
             if messagebox.askokcancel("Quit", "Do you want to quit Breakout?", parent=root_tk):
                pygame.quit()
                if root_tk: root_tk.destroy()
        else: # Pygame already quit
            if root_tk: root_tk.destroy()

    except tk.TclError: # In case root_tk is already destroyed
        pass # Just exit
    finally:
        # Ensure global flags are set such that loops terminate if not already
        global game_over_flag
        game_over_flag = True 
        if root_tk and root_tk.winfo_exists():
            root_tk.destroy() # Force destroy if not already


# --- Main Setup ---
def main():
    global pygame_screen, game_font, root_tk
    global beep_brick, beep_paddle, beep_wall, beep_lose_life

    root_tk = tk.Tk()
    root_tk.title("Pixel Retro Breakout")
    root_tk.resizable(False, False)
    
    embed_frame = tk.Frame(root_tk, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
    embed_frame.pack() 
    root_tk.update_idletasks() 
    
    os.environ['SDL_WINDOWID'] = str(embed_frame.winfo_id())
    
    pygame.init()
    # Initialize mixer with common parameters, check for success
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    except pygame.error as e:
        print(f"Warning: Pygame mixer could not be initialized: {e}. Sounds will be disabled.")
        pygame.mixer.quit() # Ensure it's considered not initialized

    pygame_screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
    
    game_font = pygame.font.Font(None, 30) 

    # Generate sounds only if mixer initialized successfully
    if pygame.mixer.get_init():
        try:
            beep_brick = generate_beep_sound(frequency=784, duration=0.05, vol=0.15)  # G5
            beep_paddle = generate_beep_sound(frequency=523, duration=0.05, vol=0.2) # C5
            beep_wall = generate_beep_sound(frequency=392, duration=0.04, vol=0.15)   # G4
            beep_lose_life = generate_beep_sound(frequency=261, duration=0.2, vol=0.3) # C4
        except Exception as e:
            print(f"Warning: Could not generate sounds: {e}")
    else:
        print("Sounds disabled as mixer failed to initialize.")

    root_tk.protocol("WM_DELETE_WINDOW", on_tk_close) # Set protocol after sounds in case of early close
    start_new_full_game() 
    root_tk.after(100, game_loop_tk) 
    root_tk.mainloop()

if __name__ == '__main__':
    main()
