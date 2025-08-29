from ursina import *
import random
from collections import deque

app = Ursina()
window.title = "3D Snake - Ursina"
window.borderless = False
window.fps_counter.enabled = True
window.exit_button.visible = False

# ------------------------
# Config
# ------------------------
GRID_W, GRID_H = 20, 20       # grid size (X x Z)
CELL_Y = 0.5                  # height for cubes
TICK_START = 0.18             # initial move interval (seconds)
SPEEDUP_EVERY = 4             # speed up after this many foods
SPEEDUP_FACTOR = 0.93         # multiply interval by this factor to speed up
WRAP_AROUND = False           # set True if you prefer wrapping instead of wall death

# Colors
COLOR_HEAD = color.azure
COLOR_BODY = color.rgb(60, 170, 220)
COLOR_FOOD = color.red
COLOR_FLOOR = color.rgb(30, 120, 50)
COLOR_WALL = color.gray

# Camera
camera.position = (GRID_W/2, 22, -8)
camera.rotation_x = 60
DirectionalLight(y=3, z=-3, shadows=True)

# Floor
floor = Entity(model="plane", collider="box",
               scale=(GRID_W, 1, GRID_H),
               position=(GRID_W/2-0.5, 0, GRID_H/2-0.5),
               color=COLOR_FLOOR)

# Walls (only if not wrapping)
walls = []
if not WRAP_AROUND:
    # North/South long bars
    for x in range(GRID_W):
        walls.append(Entity(model='cube', collider='box', color=COLOR_WALL,
                            position=(x, CELL_Y, -0.5), scale=(1, 1, 1)))
        walls.append(Entity(model='cube', collider='box', color=COLOR_WALL,
                            position=(x, CELL_Y, GRID_H - 0.5 + 1), scale=(1, 1, 1)))
    # West/East long bars
    for z in range(GRID_H):
        walls.append(Entity(model='cube', collider='box', color=COLOR_WALL,
                            position=(-0.5, CELL_Y, z), scale=(1, 1, 1)))
        walls.append(Entity(model='cube', collider='box', color=COLOR_WALL,
                            position=(GRID_W - 0.5 + 1, CELL_Y, z), scale=(1, 1, 1)))

# UI
score = 0
best = 0
tick_interval = TICK_START
tick_accum = 0.0
paused = False
game_over = False
foods_eaten = 0

score_text = Text(text=f"Score: {score}", x=-.86, y=.45, scale=1.1)
best_text = Text(text=f"Best: {best}", x=-.86, y=.40, scale=1.0)
tip_text = Text(text="WASD/Arrows: Move  |  P: Pause  |  R: Restart",
                x=-.86, y=.35, scale=.85)

# ------------------------
# Snake data
# ------------------------
# Snake stored as deque of (x, z) grid cells. Head = leftmost.
start_pos = (GRID_W//2, GRID_H//2)
snake_cells = deque([start_pos, (start_pos[0]-1, start_pos[1]), (start_pos[0]-2, start_pos[1])])
snake_set = set(snake_cells)  # quick collision lookup

# Visual cubes for snake segments (parallel to deque)
snake_blocks = []
def spawn_block(pos, is_head=False):
    x, z = pos
    block = Entity(model='cube', color=COLOR_HEAD if is_head else COLOR_BODY,
                   position=(x, CELL_Y, z), scale=(0.98, 0.98, 0.98), collider=None)
    return block

for i, cell in enumerate(snake_cells):
    snake_blocks.append(spawn_block(cell, is_head=(i == 0)))

# Movement direction: (dx, dz). Start moving +X.
dir_x, dir_z = 1, 0
next_dir = (1, 0)  # buffer to avoid instant reverse mid-tick

# ------------------------
# Food
# ------------------------
food = None

def random_empty_cell():
    while True:
        c = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
        if c not in snake_set:
            return c

def place_food():
    global food
    pos = random_empty_cell()
    if food:
        destroy(food)
    food = Entity(model='sphere', color=COLOR_FOOD,
                  position=(pos[0], CELL_Y, pos[1]), scale=0.6, collider=None)
    food.grid = pos

place_food()

# Sound (optional)
def ping(p=1.0):
    try:
        Audio('sweep', pitch=p, volume=0.45, autoplay=True)
    except Exception:
        pass

# ------------------------
# Helpers
# ------------------------
def valid_turn(cur, new):
    """prevent 180° reverse: current and new can't be exact opposites"""
    return not (cur[0] == -new[0] and cur[1] == -new[1])

def move_snake():
    """Advance snake one cell; return False if death."""
    global dir_x, dir_z, snake_cells, snake_blocks, snake_set
    global score, best, foods_eaten, tick_interval, game_over

    # apply buffered direction
    if valid_turn((dir_x, dir_z), next_dir):
        dir_x, dir_z = next_dir

    head_x, head_z = snake_cells[0]
    nx, nz = head_x + dir_x, head_z + dir_z

    # wrapping or wall collision
    if WRAP_AROUND:
        nx %= GRID_W
        nz %= GRID_H
    else:
        if not (0 <= nx < GRID_W and 0 <= nz < GRID_H):
            return False

    new_head = (nx, nz)

    # self collision (except tail cell if we move without eating)
    tail = snake_cells[-1]
    if new_head in snake_set and new_head != tail:
        return False

    # check food
    ate = (food and new_head == food.grid)

    # move data
    snake_cells.appendleft(new_head)
    snake_set.add(new_head)

    # add visual head
    head_block = spawn_block(new_head, is_head=True)
    snake_blocks.insert(0, head_block)

    # demote old head color to body
    if len(snake_blocks) > 1:
        snake_blocks[1].color = COLOR_BODY

    if ate:
        # keep tail (grow)
        ping(1.3)
        score += 1
        foods_eaten += 1
        score_text.text = f"Score: {score}"
        place_food()

        # speed up every few foods
        if foods_eaten % SPEEDUP_EVERY == 0:
            tick_interval = max(0.06, tick_interval * SPEEDUP_FACTOR)
    else:
        # pop tail
        snake_cells.pop()
        snake_set.remove(tail)
        tail_block = snake_blocks.pop()
        destroy(tail_block)

    # best score
    if score > best:
        best_text.text = f"Best: {score}"

    return True

def show_game_over():
    global game_over, best
    game_over = True
    ping(0.6)
    Text("💀 Game Over!\n\nPress R to Restart",
         origin=(0,0), background=True, scale=1.5, z=-2)

# ------------------------
# Main loops
# ------------------------
def input(key):
    global next_dir, paused
    if key in ('w', 'up arrow'):
        next_dir = (0, -1)
    elif key in ('s', 'down arrow'):
        next_dir = (0, 1)
    elif key in ('a', 'left arrow'):
        next_dir = (-1, 0)
    elif key in ('d', 'right arrow'):
        next_dir = (1, 0)

    elif key.lower() == 'p' and not game_over:
        paused = not paused
        tip_text.text = "Paused  |  P: Resume  |  R: Restart" if paused \
                        else "WASD/Arrows: Move  |  P: Pause  |  R: Restart"

    elif key.lower() == 'r':
        application.reset()

def update():
    global tick_accum
    if game_over or paused:
        return

    # spin the food slightly for flair
    if food:
        food.rotation_y += time.dt * 120

    tick_accum += time.dt
    if tick_accum >= tick_interval:
        tick_accum = 0.0
        alive = move_snake()
        if not alive:
            show_game_over()

app.run()
