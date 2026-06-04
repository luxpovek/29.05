from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
from pathlib import Path

app = Ursina()

BASE_DIR = Path(__file__).resolve().parent

# =================================================
# НАСТРОЙКИ ОКНА И ЭКРАНА
# =================================================
window.title = 'SLENDER NIGHTMARE: THE LABYRINTH'
window.fps_counter.enabled = True
window.borderless = False
window.fullscreen = False
mouse.locked = False

# =================================================
# ЗАГРУЗКА ТЕКСТУР СТЕН И ПОЛА
# =================================================
wall_tex = load_texture('assets/textures/wall.jpg')
floor_tex = load_texture('assets/textures/floor.jpg')

# Звуки
path_pickup = str(BASE_DIR / 'assets' / 'sounds' / 'pickup.wav.wav')
path_jumpscare = str(BASE_DIR / 'assets' / 'sounds' / 'jumpscare.wav.wav')
path_trap = str(BASE_DIR / 'assets' / 'sounds' / 'trap.wav.wav')

snd_pickup = Audio(path_pickup, loop=False, autoplay=False)
snd_jumpscare = Audio(path_jumpscare, loop=False, autoplay=False)
snd_trap = Audio(path_trap, loop=False, autoplay=False)

# =================================================
# СЮЖЕТНЫЙ ЭКРАН СТАРТА
# =================================================
story = Text(
    text="YOU ARE LOST IN THE LABYRINTH...\n\nFIND 3 PAGES AND ESCAPE THE SLENDER.",
    origin=(0, 0),
    scale=2,
    color=color.red,
    background=True
)

def start_game():
    story.enabled = False
    mouse.locked = True

invoke(start_game, delay=4)

# =================================================
# ОСВЕЩЕНИЕ
# =================================================
AmbientLight(color=color.rgba(40, 40, 45, 255)) 

# =================================================
# КАРТА ЛАБИРИНТА
# =================================================
maze = [
"111111111111111111111111111",
"100000000000000000000000001",
"101111111011111111011111101",
"101000001010000001010000101",
"101011101010111101010110101",
"101000101010100001010000101",
"101110101011101111011101101",
"100010100000100000000010001",
"111010111111111111111010111",
"100010000000000000000010001",
"101111111011111111111110101",
"101000001010000000000010101",
"101011101010111111101010101",
"101000101010100000101010101",
"101110101010101110101010101",
"100000101000100010001000001",
"111111111111111111111111111"
]

CELL = 3.0   
WALL_H = 5.0 

# Атмосферный пол с текстурой
ground = Entity(
    model='plane',
    scale=(200, 1, 200),
    texture=floor_tex if floor_tex else 'white_cube',
    color=color.gray if not floor_tex else color.white,
    texture_scale=(60, 60),
    collider='box',
    position=((len(maze[0]) * CELL) / 2, 0, (len(maze) * CELL) / 2)
)

# Стены лабиринта с текстурой
for z in range(len(maze)):
    for x in range(len(maze[z])):
        if maze[z][x] == '1':
            Entity(
                model='cube',
                texture=wall_tex if wall_tex else 'white_cube',
                color=color.dark_gray if not wall_tex else color.white,
                collider='box',
                position=(x * CELL, WALL_H / 2, z * CELL),
                scale=(CELL, WALL_H, CELL)
            )

# =================================================
# ИГРОК И ФОНАРИК
# =================================================
player = FirstPersonController(
    position=(1 * CELL, 1, 1 * CELL),
    speed=6,
    jump_height=0 
)

flashlight = SpotLight(parent=camera, position=(0,0,0), scale=1, color=color.white, intensity=30)
flashlight.look_at(Vec3(0,0,10))

# =================================================
# ИНТЕРФЕЙС И ТАЙМЕР ЛОВУШКИ
# =================================================
ui = Text(text="Pages: 0/3", position=(-0.85, 0.45), scale=2, color=color.white)
msg = Text(text="", origin=(0, 0), scale=3, color=color.red)

trap_timer_text = Text(text="", origin=(0, 0), scale=5, color=color.yellow, enabled=False)

is_stunned = False
stun_timer = 0.0

# =================================================
# 3 СТРАНИЦЫ (СВЕТЯЩИЕСЯ КРАСНЫЕ СФЕРЫ-КРИСТАЛЛЫ)
# =================================================
page_positions = [(5, 3), (13, 7), (21, 11)]
pages = []
collected = 0

for pos in page_positions:
    p = Entity(
        model='sphere',           
        color=color.red,          # Без текстур, чтобы гарантировать 100% видимость во тьме
        position=(pos[0] * CELL, 1.5, pos[1] * CELL), 
        scale=(0.6, 0.6, 0.6),   
        collider=None 
    )
    pages.append(p)

# =================================================
# СЛЕНДЕР ИИ (КОНТРАСТНЫЙ ЧЕРНО-БЕЛЫЙ СИЛУЭТ)
# =================================================
slender = Entity(
    model='cube',
    color=color.black,            
    scale=(1.0, 4.5, 1.0),
    position=(24 * CELL, 2.25, 14 * CELL),
    collider='box',
    double_sided=True  
)
# Белая голова, отлично отражающая свет фонаря
Entity(
    parent=slender, 
    model='sphere', 
    color=color.white, 
    scale=(0.9, 0.22, 0.9), 
    position=(0, 0.52, 0),
    double_sided=True
)

slender_speed = 2.0
teleport_timer = 0

# =================================================
# 1 ЛОВУШКА (СИНИЙ НЕОНОВЫЙ ДИСК)
# =================================================
trap = Entity(
    model='cylinder',
    color=color.cyan,               
    scale=(CELL * 0.5, 0.05, CELL * 0.5),
    position=(15 * CELL, 0.01, 3 * CELL),
    collider=None 
)

# ЗОНА ВЫХОДА
escape_zone = Entity(
    model='cube',
    color=color.rgba(0, 255, 0, 40),
    scale=(4, 6, 4),
    position=(13 * CELL, 3, 1 * CELL), 
    collider=None,
    visible=False
)

def reset_player():
    player.position = (1 * CELL, 1, 1 * CELL)

# =================================================
# ИГРОВОЙ ЦИКЛ
# =================================================
def update():
    global collected, slender_speed, teleport_timer, is_stunned, stun_timer

    if story.enabled:
        return

    # Логика работы таймера ловушки (Остановка на 5 секунд)
    if is_stunned:
        stun_timer -= time.dt
        player.speed = 0  
        
        if stun_timer > 0:
            trap_timer_text.text = str(int(stun_timer) + 1)
        else:
            is_stunned = False
            trap_timer_text.enabled = False
            player.speed = 6  # Возвращаем ходьбу
            # Перемещаем ловушку, чтобы игрок мог спокойно пойти дальше
            trap.x = random.randint(2, 20) * CELL
            trap.z = random.randint(2, 12) * CELL
        return 

    # 1. Вращение и сбор страниц
    for p in pages:
        if p.enabled:
            p.rotation_y += time.dt * 90 
            
            if distance_2d(player.position, p.position) < 1.8:
                p.disable()
                collected += 1
                if snd_pickup.clip: snd_pickup.play()
                ui.text = f"Pages: {collected}/3"
                
                if collected == 3:
                    msg.text = "FIND THE GREEN EXIT ZONE!"
                    escape_zone.visible = True

    # 2. ИИ Перемещение Слендера
    dist_to_player = distance_2d(player.position, slender.position)

    if dist_to_player < 35:
        direction = Vec3(player.x - slender.x, 0, player.z - slender.z).normalized()
        slender.position += direction * time.dt * slender_speed
        slender.look_at(Vec3(player.x, slender.y, player.z)) 

    slender_speed = 3.6 if dist_to_player < 12 else 2.2

    # Случайные телепортации Слендера по карте
    teleport_timer += time.dt
    if teleport_timer > 12.0 or (dist_to_player > 45 and random.randint(0, 100) == 1):
        rx = random.randint(2, len(maze[0]) - 3)
        rz = random.randint(2, len(maze) - 3)
        if maze[rz][rx] == '0':
            slender.position = (rx * CELL, 2.25, rz * CELL)
            teleport_timer = 0

    # 3. Нападение Слендера (Скример и смерть)
    if dist_to_player < 2.2:
        if snd_jumpscare.clip: snd_jumpscare.play()
        msg.text = "YOU DIED..."
        msg.fade_out(duration=2)
        reset_player()
        slender.position = (24 * CELL, 2.25, 14 * CELL)

    # 4. Проверка наступания на ловушку
    if distance_2d(player.position, trap.position) < 1.4:
        if snd_trap.clip: snd_trap.play()
        is_stunned = True
        stun_timer = 5.0
        trap_timer_text.enabled = True

    # 5. Условие победы в зеленой зоне
    if collected == 3 and distance_2d(player.position, escape_zone.position) < 2.5:
        msg.text = "YOU ESCAPED THE LABYRINTH!"
        msg.color = color.green
        slender.disable()
        player.speed = 0

app.run()