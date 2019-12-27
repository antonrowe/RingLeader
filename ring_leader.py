"""
Ring Leader
"""

import pgzrun
from math import atan2
from pygame.time import Clock

from ship import Ship
from bubble import *
from alerts import *

# Configuration Constants-------------------------------------------------------
BOARD_HEIGHT = 20 #Height of screen in Bubbles
# Total Width of the screen based on bubbles
WIDTH = (Bubble.BUBBLE_DIAMETER * Bubble_Grid.BOARD_WIDTH 
         + Bubble_Grid.BUBBLE_PADDING * (Bubble_Grid.BOARD_WIDTH-1) 
         + Bubble_Grid.MARGINS * 2)
# Total Height of the screen based on bubbles
HEIGHT = (Bubble.BUBBLE_DIAMETER*BOARD_HEIGHT 
          + Bubble_Grid.BUBBLE_PADDING * BOARD_HEIGHT)
HIT_GROW = Bubble.BUBBLE_DIAMETER//4 #growth when struck by a falling bubble
BLACK = (0,0,0)       # Background Color

#Multiline String Games message constants
PAUSE_MESSAGE = """PAUSED
(unpause with 'p' key)
(restart with 'r' key)
(view instructions with i)"""
INSTRUCTIONS = """Controls
- Maneuver Ship with W,A,S,D
- Aim with mouse and crosshairs
- Left Mouse Button Fires Bubbles
- Space Bar cycles available colors
- Right click to speed out the next row
- p to pause game
- r to restart game

Gameplay
- Fire bubbles to make rows and columns of 
  4 consecutive bubbles of the same color.
- Maneuver your ship to avoid all Bubbles. 
- Bubbles creeping downward will destroy your ship on contact.
- Falling bubbles which strike your ship will cause it to grow.

Scoring
- Awarded points scale exponentially with the number 
  of bubbles popped in a single combo. Bubbles created 
  by player bullets do not score points.
- You cannot score more points than required to reach 
  the next level with a combo.
- Points are awarded for any falling bubbles 
  which do not strike the player's vessel.
- Points are deducted for any bullets which fly out of bounds.

Press 'I' to return to pause screen"""
GAME_OVER_MSG = """GAME OVER
press 'r' to play again"""

# 3, 4, 5 color lists for difficulty level
COLOR_LEVELS = [[(173, 207, 25),(25, 207, 195),(186, 25, 207)], # 3 color
           [(207, 195, 25),(25, 207, 55),(25, 70, 207),(198, 25, 207)], #4 color
  [(199, 196, 28),(37, 199, 28),(28, 199, 193),(65, 28, 199),(199, 28, 188)]] #5

# Procedure starts / restarts the game when the 'r' key is pressed
def initalize_game():
    global bubble_grid, droppers, ship, bullets, score, speed_rows,\
           score_alerts, delta, \
           game_state, level, next_level_points, level_colors, cross_hair, c\
    
    bubble_grid = Bubble_Grid(COLOR_LEVELS[0])
    # list of all bubbles broken free from grid and falling 
    droppers = Dropper_List()
    # List of bullets fired from the player's ship
    bullets = Bullet_List()
    level_colors = COLOR_LEVELS[0] #start with 3 colors and increase
    ship = Ship((WIDTH // 2 + Bubble.BUBBLE_DIAMETER // 2, 
                 HEIGHT - 2*Bubble.BUBBLE_DIAMETER),
                 COLOR_LEVELS[0],
                 Bubble.BUBBLE_DIAMETER,
                 Ship.SHIP_ACCEL*Bubble.BUBBLE_DIAMETER)
    # Displayed briefly on screen when points are earned/lost
    score_alerts = Alerts_List()
    cross_hair = (0,0) #starts here and follows mouse
    score = 0
    game_state = 1 #1: Normal Play, 0: Game Over, 3: Paused, 5: Instruction Screen
    level = 1 # Levels progresses with player score
    next_level_points = 500 # To get to level 2
    new_level_msg = None # Displayed briefly at level changes
    c = Clock()
    delta = [0]
    speed_rows = Bubble_Grid.MATCH_LENGTH

# Global Data Structures--------------------------------------------------------
bubble_grid = None
droppers = None
bullets = None
level_colors = None
ship = None
score_alerts = None
cross_hair = None
score = None
combo_bullets = None 
combo_bubbles = None 
game_state = None 
level = None 
next_level_points = None 
new_level_msg = None 
c = None
delta = None
speed_rows = None

initalize_game()

# PGZero's global draw() function
def draw():
    screen.fill(BLACK) # Background
    bubble_grid.draw(screen)
    ship.draw(screen)
    bullets.draw(screen)
    droppers.draw(screen)
    draw_cross_hair()
    score_alerts.draw(screen, WIDTH)
    # Draws the score and next level threshold in bottom left 
    screen.draw.text(str(int(score))+'/'+str(next_level_points)
                     , bottomleft=(10, HEIGHT-10))
    if new_level_msg: # Briefly introduce changes for a level
        screen.draw.text(new_level_msg , centery=(HEIGHT//4), centerx=WIDTH//2)
    if not game_state:
        screen.draw.text(GAME_OVER_MSG , centery=HEIGHT//2, centerx=WIDTH//2)
    elif game_state == 3:
        screen.draw.text(PAUSE_MESSAGE, centery=HEIGHT//2, centerx=WIDTH//2)
    elif game_state == 5:
        screen.fill(BLACK) # Declutter for redaing instructions
        screen.draw.text(INSTRUCTIONS, topleft=(350,150))

# Procedure draws cross hairs to match player selected bullet color
def draw_cross_hair():
    x, y = cross_hair
    c = ship.get_color()
    b = Bubble.BUBBLE_DIAMETER
    screen.draw.line((x-b//2, y), (x-b//4, y), c)
    screen.draw.line((x+b//2, y), (x+b//4, y), c)
    screen.draw.line((x, y-b//2), (x, y-b//4), c)
    screen.draw.line((x, y+b//2), (x, y+b//4), c)

# PGZero's global update game loop
def update():
    delta[0] = c.tick()
    if game_state == 1: # Normal Game Play
        update_bullets()
        update_droppers()
        update_kill_bubbles()
        ship.update(delta[0], keyboard, keys, WIDTH, HEIGHT)
        score_alerts.update(delta, HEIGHT)
        if score >= next_level_points: # Triger level change
            next_level()

# Procedure updates player fired bullets
# Modifies global bullets list when bullets fly off screen or strike bubble grid
# Modifies global score to penalize player for errant bullets
# Calls the bullet_collide function do determine if a bullet strikes the KB grid
def update_bullets():
    global score, score_alerts
    
    cnt = 0
    while cnt < len(bullets):
        b = bullets[cnt]
        b.move(delta[0])
        
        # Check for bullet off screen
        if b.is_off_screen(HEIGHT, WIDTH):
            score_alerts += Alert(b.x, b.y, Bullet.LOST_BULLET_PENALTY, 
                                  Alert.SCORE_DURATION, Alert.SCORE_VELOCITY)
            score += Bullet.LOST_BULLET_PENALTY
            if score < 0: # Don't drop score below 0
                score = 0
            del bullets[cnt]
        
        # Check for collision with grid
        elif bubble_grid.bullet_collide(b.x, b.y, b.color):
            del bullets[cnt]
        
        else:
            cnt += 1

# Procedure updates kill bubble grid.
# 1. Remove the bottom row of bubbles if off screen
# 2. Call add_bubble_row() to add a new row of kill bubbles at top if needed
# 3. Call hit_ship() to end the game if any kill bubbles strike player ship
# 4. Move all bubbles downward by global bubble_velocity.
# 5. Call delete_bubble_matches() to match any bubbles of same color chains
# 6. Call drop_loose_bubbles() to drop bubbles not connected to top row of grid
# Modifies global kill_bubbles
def update_kill_bubbles():
    global speed_rows, droppers, game_state
    
    if bubble_grid and bubble_grid[0][0].y > HEIGHT + Bubble.BUBBLE_DIAMETER//2:
        del bubble_grid[0] # fell off screen
        
    # add a new row at top of screen
    if not bubble_grid or \
           bubble_grid[-1][0].y >= Bubble.BUBBLE_DIAMETER//2 \
                                   + Bubble_Grid.BUBBLE_PADDING:
        
        if speed_rows: # speed out a few rows at level begining
            speed_rows -=1

        bubble_grid.addTopRow()

    delta_y = bubble_grid.velocity * delta[0]
    if speed_rows:
        delta_y *= 16
    for row in bubble_grid:
        for b in row:
            if b.color: # Only bubbles with a color 'exist'
                if ship.hit_ship(b.x, b.y, Bubble.BUBBLE_DIAMETER//2):
                    game_state = 0
            
            b.y += delta_y
            
    delete_bubble_matches()
    
    droppers += bubble_grid.drop_loose_bubbles()

# Procedure updates falling bubbles which may fall off the screen, hit the 
#  player's ship, or land back on the kill bubble grid. Points are awarded for
#  falling bubbles leaving the screen.  All falling bubbles accelerate downward
#  away from the grid location from which they fell.
# Calls hit_ship() and falling_bubble_lands() to determine colisions.
# Modifies globals score and falling_bubbles
def update_droppers():
    #[[x_pos, y_pos, color, vely, column], ...more droppers]
    global score, score_alerts
    cnt = 0
    while cnt < len(droppers):
        fb = droppers[cnt]
        if fb.y > HEIGHT: # fell off screen. Award points and remove
            score += Dropper.FALLING_BUBBLE_POINTS
            score_alerts += Alert(fb.x, fb.y, Dropper.FALLING_BUBBLE_POINTS, 
                                 Alert.SCORE_DURATION, Alert.SCORE_VELOCITY)
            del droppers[cnt]
        
        # struck the ship or landed back on the kill bubble grid
        elif ship.hit_ship(fb.x,fb.y, Bubble.BUBBLE_DIAMETER//2):
            del droppers[cnt]
            ship.final_radius += HIT_GROW
        
        elif falling_bubble_lands(fb):
            del droppers[cnt]
        
        else: # accelerate normally downward
            droppers[cnt].y += fb.vely * delta[0]
            droppers[cnt].vely += Dropper.BUBBLE_GRAVITY * delta[0]
            cnt += 1

# Function returns True if a falling bubble lands on the kill bubble grid and 
#  false otherwise.
def falling_bubble_lands(fb):
    y, c, j = fb.y, fb.color, fb.column
    d = Bubble.BUBBLE_DIAMETER + Bubble_Grid.BUBBLE_PADDING
    for i, row in enumerate(bubble_grid):
        b = row[j] # only check in the faller's column
        if b.color and abs(b.y - y) <= d:
            bubble_grid[i+1][j].color = c
            return True
    return False

def delete_bubble_matches():
    global score, combo_bullets, combo_bubbles, score_alerts
    
    if not bubble_grid:
        return
    
    matches = bubble_grid.get_matches()

    for i, j in matches:
        combo_bullets = 0
        combo_bubbles = 0
        rec_erase(i,j)
        if combo_bullets and combo_bubbles:
            bonus = 2**combo_bubbles
            score_diff = next_level_points - score
            if bonus > score_diff:
                bonus = score_diff
            score += bonus
            x, y = bubble_grid[i][j].x, bubble_grid[i][j].y
            score_alerts += Alert(x, y, bonus, 
                                 Alert.SCORE_DURATION, Alert.SCORE_VELOCITY)

def rec_erase(i,j):
    global combo_bubbles, combo_bullets
    
    c = bubble_grid[i][j].color
    
    if not c:
        return    

    if bubble_grid[i][j].bulletFlag:
        combo_bullets += 1
    else:
        combo_bubbles += 1
    
    bubble_grid[i][j].color = None
    
    n = ((i+1,j), (i-1,j), (i, j+1), (i, j-1))
    for nei in n:
        i, j = nei
        if (i in range(len(bubble_grid)) 
                and j in range(Bubble_Grid.BOARD_WIDTH)
                and bubble_grid[i][j].color == c):
            rec_erase(i, j)

def on_mouse_move (pos):
    global cross_hair
    cross_hair = pos

def on_mouse_down (pos, button):
    global bubble_velocity, speed_rows, bullets
    if mouse.LEFT == button:
        bullets += Bullet(ship.x, ship.y, ship.get_color(), get_angle(pos))
    if mouse.RIGHT == button:
        speed_rows += 1

def on_key_down(key):
    global game_state
    if key == keys.SPACE:
        ship.cycle_color()
    if key == keys.P:
        if game_state == 3:
            game_state = 1
        elif game_state == 1:
            game_state = 3
    if key == keys.R:
        initalize_game()
    if key == keys.I:
        if game_state == 3:
            game_state = 5
        elif game_state == 5:
            game_state = 3

def get_angle(pos):
    return atan2(ship.y - pos[1], - (ship.x - pos[0]))

def next_level():
    global level, bubble_velocity, bubble_grid, bullets, next_level_points, \
        droppers, new_level_msg, speed_rows, level_colors
    
    droppers = Dropper_List()
    bullets = Bullet_List()
    ship.reset_hull_size()
    level += 1
    speed_rows = Bubble_Grid.MATCH_LENGTH
    next_level_points += 250 * level
    
    new_level_msg = f"Level {level}\nBubble Creation Rate +10%"
    
    if level == 5:
        level_colors = COLOR_LEVELS[1]
        new_level_msg += "\nNew Color Added!"
        ship.set_colors(level_colors)
    elif level == 10:
        level_colors = COLOR_LEVELS[2]
        new_level_msg += "\nNew Color Added!"
        ship.set_colors(level_colors)

    bubble_grid = Bubble_Grid(level_colors, bubble_grid.velocity * 1.1)
    clock.schedule(clear_new_level_msg, 10.0)

def clear_new_level_msg():
    global new_level_msg
    new_level_msg = None

pgzrun.go()