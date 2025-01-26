import pygame
import sys
import os
import webbrowser
from pygame.locals import *

# Initialize Pygame and center window
pygame.init()
os.environ['SDL_VIDEO_CENTERED'] = '1'

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PURPLE = (128, 0, 128)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)

# Game parameters
BALL_RADIUS = 10
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
BALL_SPEED_X = 4
BALL_SPEED_Y = 4

# Slider parameters
SLIDER_WIDTH = 200
SLIDER_HEIGHT = 20
HANDLE_SIZE = 15

# Game state
game_state = {
    'paused': False,
    'score': 0,
    'current_screen': 'menu',
    'control_mode': 'ai',  # 'ai' or 'human'
    'milestone_message': None,
    'message_timer': 0
}

# AI state
ai_state = {
    'miss_streak': 0,
    'correction': 0,
    'last_actual_x': None,
    'learning_active': False
}

# Set up borderless window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("AI Paddle Game")
font = pygame.font.Font(None, 36)
title_font = pygame.font.Font(None, 72)

# Game area dimensions
GAME_AREA = pygame.Rect(50, 50, SCREEN_WIDTH-100, SCREEN_HEIGHT-150)

# Initialize game elements
paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
paddle_y = SCREEN_HEIGHT - 60
ball_x = GAME_AREA.centerx
ball_y = GAME_AREA.centery
ball_dx = BALL_SPEED_X * (1 if pygame.time.get_ticks() % 2 else -1)
ball_dy = BALL_SPEED_Y
ball_color = RED

# Slider configurations
sliders = {
    'speed': {
        'rect': pygame.Rect(50, SCREEN_HEIGHT - 100, SLIDER_WIDTH, SLIDER_HEIGHT),
        'val': 2.5,
        'min': 0.1,
        'max': 5.0,
        'label': "Paddle Speed"
    }
}

def reset_game():
    """Reset all game elements to initial state"""
    global paddle_x, ball_x, ball_y, ball_dx, ball_dy, ball_color
    game_state.update({
        'score': 0,
        'paused': False
    })
    paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
    ball_x = GAME_AREA.centerx
    ball_y = GAME_AREA.centery
    ball_dx = BALL_SPEED_X * (1 if pygame.time.get_ticks() % 2 else -1)
    ball_dy = BALL_SPEED_Y
    ball_color = RED
    ai_state.update({
        'miss_streak': 0,
        'correction': 0,
        'last_actual_x': None,
        'learning_active': False
    })

def simulate_trajectory(steps):
    """Predict ball position after specified steps including wall bounces"""
    px, py, dx, dy = ball_x, ball_y, ball_dx, ball_dy
    remaining = steps
    
    while remaining > 0 and py < paddle_y:
        px += dx
        py += dy
        remaining -= 1
        
        # Handle wall collisions
        if px - BALL_RADIUS < GAME_AREA.left or px + BALL_RADIUS > GAME_AREA.right:
            dx *= -1
        if py - BALL_RADIUS < GAME_AREA.top:
            dy *= -1
            
    return px

def calculate_ai_target():
    """Calculate AI target position with bounce prediction and learning"""
    if ball_dy <= 0:
        return paddle_x
    
    steps = int((paddle_y - ball_y) / ball_dy)
    scaled_steps = int(steps * 5.0)  # Fixed prediction horizon
    
    predicted_x = simulate_trajectory(scaled_steps)
    
    # Apply learning correction with fixed rate
    if ai_state['miss_streak'] >= 3 and ai_state['last_actual_x']:
        error = ai_state['last_actual_x'] - (paddle_x + PADDLE_WIDTH/2)
        predicted_x += error * 5.0  # Fixed learning rate
        ai_state['learning_active'] = True
    else:
        ai_state['learning_active'] = False
    
    return max(GAME_AREA.left, min(predicted_x - PADDLE_WIDTH/2, GAME_AREA.right - PADDLE_WIDTH))

def move_paddle():
    """Smoothly move paddle towards target position"""
    target = calculate_ai_target()
    speed = sliders['speed']['val']
    
    if paddle_x < target - speed:
        return paddle_x + speed
    if paddle_x > target + speed:
        return paddle_x - speed
    return target

def draw_slider(slider):
    """Render slider component"""
    pygame.draw.rect(screen, GRAY, slider['rect'])
    handle_x = slider['rect'].left + ((slider['val'] - slider['min']) / 
                (slider['max'] - slider['min'])) * SLIDER_WIDTH
    pygame.draw.rect(screen, YELLOW, 
                    (handle_x - HANDLE_SIZE//2, slider['rect'].centery - HANDLE_SIZE//2,
                     HANDLE_SIZE, HANDLE_SIZE))
    label = font.render(slider['label'], True, WHITE)
    screen.blit(label, (slider['rect'].left, slider['rect'].top - 30))
    value = font.render(f"{slider['val']:.1f}", True, WHITE)
    screen.blit(value, (slider['rect'].right + 10, slider['rect'].top))

def handle_slider_input(slider, x_pos):
    """Update slider value based on mouse position"""
    slider['val'] = slider['min'] + ((x_pos - slider['rect'].left) / 
                   SLIDER_WIDTH) * (slider['max'] - slider['min'])
    slider['val'] = max(slider['min'], min(slider['val'], slider['max']))

def draw_interface():
    """Draw all UI elements"""
    # Show control mode indicator only when not paused
    if not game_state['paused']:
        mode_text = font.render(f"Mode: {game_state['control_mode'].upper()}", True, CYAN)
        text_rect = mode_text.get_rect(center=(SCREEN_WIDTH//2, 20))
        screen.blit(mode_text, text_rect)

    # Score display
    score_text = font.render(f"Score: {game_state['score']}", True, WHITE)
    screen.blit(score_text, (20, 20))

    # Show milestone message if exists
    if game_state['milestone_message'] and game_state['message_timer'] > 0:
        message = font.render(game_state['milestone_message'], True, YELLOW)
        msg_rect = message.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4))
        screen.blit(message, msg_rect)
        game_state['message_timer'] -= 1

    # Paused overlay
    if game_state['paused']:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        text = font.render("PAUSED", True, WHITE)
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        overlay.blit(text, text_rect)
        screen.blit(overlay, (0, 0))

def draw_main_menu():
    """Draw main menu screen"""
    screen.fill(BLACK)
    title_text = title_font.render("Bouncing Paddle", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 100))
    screen.blit(title_text, title_rect)

    # Buttons
    button_width, button_height = 200, 50
    start_button = pygame.Rect(SCREEN_WIDTH//2 - button_width//2, 300, button_width, button_height)
    info_button = pygame.Rect(SCREEN_WIDTH//2 - button_width//2, 370, button_width, button_height)

    # Draw buttons
    pygame.draw.rect(screen, PURPLE, start_button)
    pygame.draw.rect(screen, PURPLE, info_button)

    # Button labels
    start_text = font.render("Start Game", True, WHITE)
    screen.blit(start_text, start_text.get_rect(center=start_button.center))
    info_text = font.render("Info", True, WHITE)
    screen.blit(info_text, info_text.get_rect(center=info_button.center))

    # Hover effects
    mouse_pos = pygame.mouse.get_pos()
    for btn in [start_button, info_button]:
        if btn.collidepoint(mouse_pos):
            pygame.draw.rect(screen, YELLOW, btn, 3)

def draw_info_screen():
    """Draw information/credits screen with clickable URLs"""
    screen.fill(BLACK)
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    
    lines = [
        ("Game created by:", None),
        ("Pedroperry - https://github.com/Pedroperry", "https://github.com/Pedroperry"),
        ("Deepseek Chat - https://chat.deepseek.com", "https://chat.deepseek.com"),
        ("Click anywhere to return", None)
    ]
    
    url_rects = []
    y_pos = SCREEN_HEIGHT//2 - 100
    for text, url in lines:
        text_color = CYAN if url else WHITE
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, y_pos))
        overlay.blit(text_surf, text_rect)
        if url:
            url_rects.append((text_rect.inflate(10, 5), url))
        y_pos += 40
    
    screen.blit(overlay, (0, 0))
    return url_rects

def check_score_milestone():
    """Check and set milestone messages based on score"""
    score = game_state['score']
    message = None
    if game_state['control_mode'] == 'human':
        if score == 5:
            message = "Nice start!"
        elif score == 10:
            message = "Getting good!"
        elif score == 20:
            message = "Amazing skills!"
        elif score == 50:
            message = "You're a master!"
        elif score % 100 == 0 and score > 0:
            message = f"Incredible! Score: {score}!"
            
    if message:
        game_state['milestone_message'] = message
        game_state['message_timer'] = 120  # Show message for 2 seconds (60fps * 2)

# Main game loop
clock = pygame.time.Clock()
running = True
dragging = None

while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                if game_state['current_screen'] == 'game':
                    game_state['current_screen'] = 'menu'
                else:
                    running = False
            elif event.key == K_SPACE and game_state['current_screen'] == 'game':
                game_state['paused'] = not game_state['paused']
            elif event.key == K_r and game_state['current_screen'] == 'game':
                reset_game()
            elif event.key == K_m:  # Toggle control mode
                if game_state['current_screen'] == 'game' and not game_state['paused']:
                    game_state['control_mode'] = 'human' if game_state['control_mode'] == 'ai' else 'ai'
        elif event.type == MOUSEBUTTONDOWN:
            if game_state['current_screen'] == 'menu':
                # Check menu button clicks
                mouse_pos = event.pos
                button_width, button_height = 200, 50
                start_button = pygame.Rect(SCREEN_WIDTH//2 - button_width//2, 300, button_width, button_height)
                info_button = pygame.Rect(SCREEN_WIDTH//2 - button_width//2, 370, button_width, button_height)
                
                if start_button.collidepoint(mouse_pos):
                    reset_game()
                    game_state['current_screen'] = 'game'
                elif info_button.collidepoint(mouse_pos):
                    game_state['current_screen'] = 'info'
            elif game_state['current_screen'] == 'info':
                url_rects = draw_info_screen()
                for rect, url in url_rects:
                    if rect.collidepoint(event.pos):
                        webbrowser.open(url)
                game_state['current_screen'] = 'menu'
            elif game_state['current_screen'] == 'game':
                # Handle slider dragging
                if game_state['control_mode'] == 'ai':  # Only allow slider interaction in AI mode
                    for name, slider in sliders.items():
                        if slider['rect'].collidepoint(event.pos):
                            dragging = name
        elif event.type == MOUSEBUTTONUP:
            dragging = None
        elif event.type == MOUSEMOTION and dragging and game_state['current_screen'] == 'game':
            if game_state['control_mode'] == 'ai':  # Only handle slider movement in AI mode
                handle_slider_input(sliders[dragging], event.pos[0])

    # Game logic
    if game_state['current_screen'] == 'game' and not game_state['paused']:
        if not game_state['paused']:
            # Handle paddle movement
            if game_state['control_mode'] == 'human':
                keys = pygame.key.get_pressed()
                if keys[K_LEFT] or keys[K_a]:
                    paddle_x = max(GAME_AREA.left, paddle_x - 10)
                if keys[K_RIGHT] or keys[K_d]:
                    paddle_x = min(GAME_AREA.right - PADDLE_WIDTH, paddle_x + 10)
            else:
                paddle_x = move_paddle()
            
            # Update ball position
            ball_x += ball_dx
            ball_y += ball_dy

            # Wall collisions
            if ball_x - BALL_RADIUS < GAME_AREA.left or ball_x + BALL_RADIUS > GAME_AREA.right:
                ball_dx *= -1
                ball_color = RED
            if ball_y - BALL_RADIUS < GAME_AREA.top:
                ball_dy *= -1
                ball_color = RED

            # Paddle collision
            if ball_y + BALL_RADIUS > paddle_y:
                paddle_rect = pygame.Rect(paddle_x, paddle_y, PADDLE_WIDTH, PADDLE_HEIGHT)
                ball_rect = pygame.Rect(ball_x - BALL_RADIUS, ball_y - BALL_RADIUS,
                                        2*BALL_RADIUS, 2*BALL_RADIUS)
                if ball_rect.colliderect(paddle_rect):
                    ball_dy *= -1
                    ball_color = PURPLE
                    game_state['score'] += 1
                    check_score_milestone()
                    ai_state.update({'miss_streak': 0, 'correction': 0})
                else:
                    game_state['score'] = 0
                    reset_game()

    # Drawing
    screen.fill(BLACK)
    
    if game_state['current_screen'] == 'menu':
        draw_main_menu()
    elif game_state['current_screen'] == 'info':
        draw_info_screen()
    elif game_state['current_screen'] == 'game':
        pygame.draw.rect(screen, WHITE, GAME_AREA, 2)
        pygame.draw.rect(screen, YELLOW, (paddle_x, paddle_y, PADDLE_WIDTH, PADDLE_HEIGHT))
        pygame.draw.circle(screen, ball_color, (int(ball_x), int(ball_y)), BALL_RADIUS)
        draw_interface()
        # Only show sliders in AI mode
        if game_state['control_mode'] == 'ai':
            for slider in sliders.values():
                draw_slider(slider)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
