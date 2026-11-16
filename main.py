"""Creature Clash - elemental monster battles.

Versus:   two players fight in an arena.
Campaign: one creature walks three mazes, shooting or dodging turret orbs.

Player 1: move W A S D, attack Left Alt  (backup key: Q)
Player 2: move I J K L, attack Right Alt (backup key: O)
In the campaign either hand's keys work. Esc returns to the menu.

Run with:  uv run main.py
"""

import array
import math
import random

import pygame

W, H = 960, 620
FPS = 60
ARENA = pygame.Rect(30, 110, W - 60, H - 140)
RADIUS = 26
MAX_LIVES = 3

BG = (24, 26, 38)
FLOOR = (46, 52, 70)
FLOOR_LINE = (58, 66, 88)
WHITE = (245, 245, 250)
DIM = (150, 156, 175)
RED = (230, 70, 80)
P_COLORS = [(255, 120, 120), (120, 190, 255)]

# name, type, body colour, accent colour, attack name,
# hp, move speed, damage, shot speed, cooldown (s), shot radius
CREATURES = [
    dict(name="Mossling", type="Grass", color=(96, 190, 96), accent=(40, 130, 60),
         attack="Leaf Dart", hp=110, speed=230, dmg=11, shot=560, cd=0.32, r=8),
    dict(name="Voltuft", type="Electric", color=(250, 215, 60), accent=(70, 220, 240),
         attack="Spark Bolt", hp=85, speed=300, dmg=9, shot=760, cd=0.24, r=7),
    dict(name="Cinderpup", type="Fire", color=(240, 130, 60), accent=(255, 220, 90),
         attack="Ember Ball", hp=95, speed=250, dmg=17, shot=500, cd=0.50, r=11),
    dict(name="Bubblefin", type="Water", color=(80, 150, 240), accent=(190, 230, 255),
         attack="Bubble Shot", hp=115, speed=240, dmg=13, shot=440, cd=0.40, r=13),
    dict(name="Pebblor", type="Rock", color=(150, 150, 160), accent=(90, 220, 190),
         attack="Boulder Toss", hp=150, speed=175, dmg=26, shot=380, cd=0.85, r=15),
    dict(name="Fluffkin", type="Normal", color=(240, 225, 195), accent=(200, 150, 110),
         attack="Star Flick", hp=100, speed=265, dmg=12, shot=600, cd=0.34, r=9),
]

KEYS = [
    dict(up=pygame.K_w, down=pygame.K_s, left=pygame.K_a, right=pygame.K_d,
         fire=(pygame.K_LALT, pygame.K_q)),
    dict(up=pygame.K_i, down=pygame.K_k, left=pygame.K_j, right=pygame.K_l,
         fire=(pygame.K_RALT, pygame.K_o)),
]

# ---- campaign: mazes on a 15 x 8 grid of 60px tiles ----
# '#' wall, '.' floor, 'S' start, 'E' exit, '< > ^ v' turret firing that way
TILE = 60
CR = 18            # creature radius inside the maze (smaller than in versus)
HERO_SPEED = 0.8   # movement multiplier inside the maze
ORB_R = 11
ORB_DMG = 25
ORB = (200, 90, 230)
WALL = (88, 98, 128)
DIRS = {">": (1, 0), "<": (-1, 0), "^": (0, -1), "v": (0, 1)}
LEVELS = [
    dict(name="Winding Path", speed=95, every=2.6, map=[
        "S....#........<",
        "####.#.######.#",
        "##...#.#......#",
        "##.###.#.######",
        "##.....#......<",
        "########.######",
        ">.............E",
        "###############"]),
    dict(name="Crossfire Halls", speed=115, every=2.0, map=[
        "S..#v....#v...#",
        "...#.....#....<",
        "...#..#..#..#..",
        ">.....#.....#..",
        "......#.....#..",
        "...#..#..#..#..",
        "...#.....#....E",
        "...#...^.#....#"]),
    dict(name="The Gauntlet", speed=135, every=1.6, map=[
        "S.#.....<.....v",
        "..#.###.#.###..",
        "..#.>.....#.#..",
        "....#.###.#....",
        ".##.#.#...#.##.",
        ".#....#.###.#..",
        ".#.####.....#.E",
        ".......#....#.^"]),
]


# --------------------------------------------------------------------------
# Sound: everything is synthesised at start-up, no asset files needed.
# --------------------------------------------------------------------------
RATE = 22050


def synth(f0, f1, dur, wave="square", vol=0.35):
    """A short tone sweeping from f0 to f1 Hz with a fade-out."""
    n = int(RATE * dur)
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += (f0 + (f1 - f0) * t) / RATE
        if wave == "square":
            s = 1.0 if phase % 1.0 < 0.5 else -1.0
        elif wave == "noise":
            s = random.uniform(-1, 1)
        else:
            s = math.sin(2 * math.pi * phase)
        buf.append(int(s * vol * (1.0 - t) * 32767))
    return buf


def melody(notes, step=0.11):
    buf = array.array("h")
    for f in notes:
        buf.extend(synth(f, f, step, "square", 0.28))
    return buf


class Sounds:
    def __init__(self):
        self.s = {}
        try:
            pygame.mixer.init(RATE, -16, 1, 512)
            raw = {
                "move": synth(520, 520, 0.05, "square", 0.2),
                "lock": synth(440, 880, 0.14, "square", 0.3),
                "shoot0": synth(900, 500, 0.10, "sine"),
                "shoot1": synth(1500, 700, 0.08, "square", 0.25),
                "shoot2": synth(500, 180, 0.16, "noise", 0.3),
                "shoot3": synth(350, 800, 0.12, "sine"),
                "shoot4": synth(170, 70, 0.20, "square", 0.3),
                "shoot5": synth(1000, 1400, 0.09, "sine"),
                "hit": synth(240, 60, 0.16, "noise", 0.5),
                "block": synth(1200, 1900, 0.07, "square", 0.25),
                "ko": synth(620, 60, 0.6, "square", 0.35),
                "go": synth(660, 990, 0.25, "square", 0.3),
                "win": melody([523, 659, 784, 1047, 784, 1047], 0.12),
            }
            self.s = {k: pygame.mixer.Sound(buffer=v.tobytes()) for k, v in raw.items()}
        except pygame.error:
            self.s = {}  # no audio device: play silently

    def play(self, name):
        snd = self.s.get(name)
        if snd:
            snd.play()


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------
def poly_points(cx, cy, r_out, r_in, n, rot=0.0):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / n
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def draw_creature(surf, idx, x, y, facing=(0, 1), t=0.0, scale=1.0, flash=False):
    c = CREATURES[idx]
    col = WHITE if flash else c["color"]
    acc = WHITE if flash else c["accent"]
    R = RADIUS * scale
    bob = math.sin(t * 6) * 2 * scale
    y += bob
    pygame.draw.ellipse(surf, (20, 22, 30),
                        (x - R * 0.8, y - bob + R * 0.75, R * 1.6, R * 0.45))

    if idx == 0:  # Mossling: round body, two leaves on top
        for side in (-1, 1):
            tip = (x + side * R * 0.9, y - R * 1.5)
            pygame.draw.polygon(surf, acc, [(x, y - R * 0.7), tip,
                                            (x + side * R * 0.75, y - R * 0.5)])
        pygame.draw.circle(surf, col, (x, y), R)
        pygame.draw.circle(surf, acc, (x - R * 0.45, y + R * 0.4), R * 0.16)
        pygame.draw.circle(surf, acc, (x + R * 0.5, y + R * 0.3), R * 0.12)
    elif idx == 1:  # Voltuft: spiky crackling ball
        pygame.draw.polygon(surf, acc, poly_points(x, y, R * 1.3, R * 0.8, 9, t * 3))
        pygame.draw.polygon(surf, col, poly_points(x, y, R * 1.15, R * 0.85, 9, -t * 2))
        pygame.draw.circle(surf, col, (x, y), R * 0.9)
    elif idx == 2:  # Cinderpup: flame crest
        for i, off in enumerate((-0.5, 0, 0.5)):
            h = R * (1.5 + 0.25 * math.sin(t * 14 + i * 2))
            pygame.draw.polygon(surf, acc if i == 1 else (255, 170, 60), [
                (x + off * R - R * 0.3, y - R * 0.6),
                (x + off * R, y - h),
                (x + off * R + R * 0.3, y - R * 0.6)])
        pygame.draw.circle(surf, col, (x, y), R)
        pygame.draw.circle(surf, WHITE if flash else (255, 225, 190),
                           (x, y + R * 0.45), R * 0.45)
    elif idx == 3:  # Bubblefin: side fins and a tail
        wag = math.sin(t * 8) * R * 0.2
        for side in (-1, 1):
            pygame.draw.polygon(surf, acc, [(x + side * R * 0.7, y - R * 0.3),
                                            (x + side * R * 1.5, y + wag),
                                            (x + side * R * 0.7, y + R * 0.4)])
        pygame.draw.polygon(surf, acc, [(x - R * 0.3, y - R * 0.8), (x, y - R * 1.4),
                                        (x + R * 0.3, y - R * 0.8)])
        pygame.draw.circle(surf, col, (x, y), R)
        pygame.draw.circle(surf, acc, (x, y + R * 0.5), R * 0.4)
    elif idx == 4:  # Pebblor: hexagonal boulder with crystals
        for off, hgt in ((-0.45, 1.35), (0.1, 1.6), (0.55, 1.25)):
            pygame.draw.polygon(surf, acc, [(x + off * R - R * 0.2, y - R * 0.7),
                                            (x + off * R, y - R * hgt),
                                            (x + off * R + R * 0.2, y - R * 0.7)])
        pygame.draw.polygon(surf, col, poly_points(x, y, R * 1.1, R * 1.02, 4, 0.3))
        pygame.draw.line(surf, (100, 100, 112), (x - R * 0.7, y + R * 0.3),
                         (x - R * 0.2, y + R * 0.7), max(1, int(3 * scale)))
    else:  # Fluffkin: puffball with round ears
        for side in (-1, 1):
            pygame.draw.circle(surf, col, (x + side * R * 0.7, y - R * 0.95), R * 0.4)
            pygame.draw.circle(surf, acc, (x + side * R * 0.7, y - R * 0.95), R * 0.2)
        for i in range(10):
            a = i * math.tau / 10 + math.sin(t * 2) * 0.1
            pygame.draw.circle(surf, col, (x + math.cos(a) * R * 0.8,
                                           y + math.sin(a) * R * 0.8), R * 0.38)
        pygame.draw.circle(surf, col, (x, y), R * 0.9)

    # eyes look where the creature is facing
    fx, fy = facing
    for side in (-1, 1):
        ex = x + side * R * 0.36 + fx * R * 0.25
        ey = y - R * 0.12 + fy * R * 0.25
        pygame.draw.circle(surf, WHITE, (ex, ey), R * 0.24)
        pygame.draw.circle(surf, (20, 20, 30),
                           (ex + fx * R * 0.1, ey + fy * R * 0.1), R * 0.12)


def draw_shot(surf, idx, x, y, r, t):
    c = CREATURES[idx]
    if idx == 3:
        pygame.draw.circle(surf, c["color"], (x, y), r, 3)
        pygame.draw.circle(surf, c["accent"], (x - r * 0.3, y - r * 0.3), r * 0.25)
    elif idx in (1, 5):
        pygame.draw.polygon(surf, c["accent"] if idx == 1 else c["color"],
                            poly_points(x, y, r * 1.5, r * 0.6, 5, t * 12))
    elif idx == 4:
        pygame.draw.polygon(surf, c["color"], poly_points(x, y, r, r * 0.85, 4, t * 5))
    elif idx == 0:
        pygame.draw.polygon(surf, c["color"], poly_points(x, y, r * 1.6, r * 0.5, 2, t * 10))
    else:
        pygame.draw.circle(surf, c["color"], (x, y), r)
        pygame.draw.circle(surf, c["accent"], (x, y), r * 0.55)


# --------------------------------------------------------------------------
# Game objects
# --------------------------------------------------------------------------
class Player:
    def __init__(self, num, idx):
        self.num = num
        self.idx = idx
        self.c = CREATURES[idx]
        self.lives = MAX_LIVES
        self.spawn()

    def spawn(self):
        self.x = ARENA.left + 110 if self.num == 0 else ARENA.right - 110
        self.y = ARENA.centery
        self.facing = (1, 0) if self.num == 0 else (-1, 0)
        self.hp = self.c["hp"]
        self.cool = 0.0
        self.flash = 0.0
        self.shield = 1.5  # brief invulnerability after (re)spawning

    def update(self, dt, keys):
        k = KEYS[self.num]
        dx = (1 if keys[k["right"]] else 0) - (1 if keys[k["left"]] else 0)
        dy = (1 if keys[k["down"]] else 0) - (1 if keys[k["up"]] else 0)
        if dx or dy:
            n = math.hypot(dx, dy)
            self.facing = (dx / n, dy / n)
            self.x += dx / n * self.c["speed"] * dt
            self.y += dy / n * self.c["speed"] * dt
        self.x = max(ARENA.left + RADIUS, min(ARENA.right - RADIUS, self.x))
        self.y = max(ARENA.top + RADIUS, min(ARENA.bottom - RADIUS, self.y))
        self.cool = max(0.0, self.cool - dt)
        self.flash = max(0.0, self.flash - dt)
        self.shield = max(0.0, self.shield - dt)

    def wants_fire(self, keys):
        return any(keys[key] for key in KEYS[self.num]["fire"])


class Shot:
    def __init__(self, owner, radius=RADIUS):
        c = owner.c
        fx, fy = owner.facing
        self.owner = owner
        self.x = owner.x + fx * (radius + c["r"])
        self.y = owner.y + fy * (radius + c["r"])
        self.vx, self.vy = fx * c["shot"], fy * c["shot"]
        self.r, self.dmg = c["r"], c["dmg"]


class Hero(Player):
    """The single campaign creature. Either hand's keys work."""

    def __init__(self, idx):
        super().__init__(0, idx)

    def place(self, x, y):
        self.spawn()
        self.x, self.y, self.facing = x, y, (1, 0)

    def update(self, dt, keys, maze):
        dx = dy = 0
        for k in KEYS:
            dx += bool(keys[k["right"]]) - bool(keys[k["left"]])
            dy += bool(keys[k["down"]]) - bool(keys[k["up"]])
        dx, dy = max(-1, min(1, dx)), max(-1, min(1, dy))
        if dx or dy:
            n = math.hypot(dx, dy)
            self.facing = (dx / n, dy / n)
            step = self.c["speed"] * HERO_SPEED * dt
            self.x += dx / n * step
            self.y += dy / n * step
        self.x, self.y = maze.push_out(self.x, self.y, CR)
        self.cool = max(0.0, self.cool - dt)
        self.flash = max(0.0, self.flash - dt)
        self.shield = max(0.0, self.shield - dt)

    def wants_fire(self, keys):
        return any(keys[key] for k in KEYS for key in k["fire"])


class Maze:
    def __init__(self, level):
        self.rows = level["map"]
        self.turrets = []  # (x, y, dx, dy) in pixels / unit direction
        for cy, row in enumerate(self.rows):
            for cx, ch in enumerate(row):
                if ch == "S":
                    self.start = self.center(cx, cy)
                elif ch == "E":
                    self.exit = self.center(cx, cy)
                elif ch in DIRS:
                    self.turrets.append((*self.center(cx, cy), *DIRS[ch]))

    @staticmethod
    def center(cx, cy):
        return (ARENA.left + cx * TILE + TILE // 2, ARENA.top + cy * TILE + TILE // 2)

    def wall(self, cx, cy):
        if not (0 <= cy < len(self.rows) and 0 <= cx < len(self.rows[0])):
            return True
        return self.rows[cy][cx] in "#<>^v"

    def wall_at(self, x, y):
        return self.wall(int((x - ARENA.left) // TILE), int((y - ARENA.top) // TILE))

    def push_out(self, x, y, r):
        """Slide a circle out of any wall tiles it overlaps."""
        for _ in range(2):
            cx0 = int((x - ARENA.left) // TILE)
            cy0 = int((y - ARENA.top) // TILE)
            for cy in range(cy0 - 1, cy0 + 2):
                for cx in range(cx0 - 1, cx0 + 2):
                    if not self.wall(cx, cy):
                        continue
                    rx, ry = ARENA.left + cx * TILE, ARENA.top + cy * TILE
                    nx = max(rx, min(rx + TILE, x))
                    ny = max(ry, min(ry + TILE, y))
                    d = math.hypot(x - nx, y - ny)
                    if 0 < d < r:
                        x += (x - nx) / d * (r - d)
                        y += (y - ny) / d * (r - d)
        return x, y


class Game:
    def __init__(self):
        self.sounds = Sounds()
        self.font = pygame.font.SysFont("consolas,couriernew", 20, bold=True)
        self.small = pygame.font.SysFont("consolas,couriernew", 15)
        self.big = pygame.font.SysFont("consolas,couriernew", 54, bold=True)
        self.t = 0.0
        self.sparks = []
        self.shake = 0.0
        self.to_menu()

    # ---- state changes ----
    def to_menu(self):
        self.state = "menu"
        self.menu = 0

    def to_select(self, mode):
        self.mode = mode
        self.state = "select"
        self.cursor = [0, 5]
        self.locked = [False, mode == "campaign"]
        self.wait = 0.0

    def start_campaign(self):
        self.hero = Hero(self.cursor[0])
        self.level = 0
        self.start_level()

    def start_level(self):
        self.state = "maze"
        self.maze = Maze(LEVELS[self.level])
        self.hero.place(*self.maze.start)
        self.shots = []
        self.orbs = []
        self.timers = [0.6 + 0.5 * i for i in range(len(self.maze.turrets))]
        self.freeze = 1.0
        self.sounds.play("go")

    def to_fight(self):
        self.state = "fight"
        self.players = [Player(0, self.cursor[0]), Player(1, self.cursor[1])]
        self.shots = []
        self.sparks = []
        self.freeze = 1.2
        self.shake = 0.0
        self.winner = None
        self.sounds.play("go")

    # ---- input ----
    def keydown(self, key):
        confirm = KEYS[0]["fire"] + KEYS[1]["fire"] + (pygame.K_RETURN, pygame.K_SPACE)
        if self.state == "menu":
            if key in (KEYS[0]["up"], KEYS[0]["down"], KEYS[1]["up"], KEYS[1]["down"]):
                self.menu = 1 - self.menu
                self.sounds.play("move")
            elif key in confirm:
                self.sounds.play("lock")
                self.to_select(("versus", "campaign")[self.menu])
        elif self.state == "select":
            for p in (0, 1):
                k = KEYS[p]
                slot = 0 if self.mode == "campaign" else p
                if key in k["fire"]:
                    self.locked[slot] = not self.locked[slot]
                    self.sounds.play("lock")
                elif not self.locked[slot]:
                    step = {k["left"]: -1, k["right"]: 1, k["up"]: -3, k["down"]: 3}.get(key)
                    if step:
                        self.cursor[slot] = (self.cursor[slot] + step) % 6
                        self.sounds.play("move")
            if all(self.locked):
                self.wait = 0.6
        elif self.state in ("over", "end") and key in (pygame.K_r, pygame.K_RETURN,
                                                       pygame.K_SPACE):
            self.to_menu()

    # ---- simulation ----
    def update(self, dt, keys):
        self.t += dt
        if self.state == "select":
            if all(self.locked):
                self.wait -= dt
                if self.wait <= 0:
                    if self.mode == "campaign":
                        self.start_campaign()
                    else:
                        self.to_fight()
            return
        self.shake = max(0.0, self.shake - dt)
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        if self.state == "maze":
            self.update_maze(dt, keys)
        elif self.state == "fight":
            self.update_fight(dt, keys)

    def update_maze(self, dt, keys):
        if self.freeze > 0:
            self.freeze -= dt
            return
        h, mz, lv = self.hero, self.maze, LEVELS[self.level]
        h.update(dt, keys, mz)
        if h.wants_fire(keys) and h.cool <= 0:
            h.cool = h.c["cd"]
            self.shots.append(Shot(h, CR))
            self.sounds.play(f"shoot{h.idx}")

        for i, (tx, ty, dx, dy) in enumerate(mz.turrets):
            self.timers[i] -= dt
            if self.timers[i] <= 0:
                self.timers[i] = lv["every"]
                self.orbs.append([tx + dx * TILE / 2, ty + dy * TILE / 2,
                                  dx * lv["speed"], dy * lv["speed"]])

        orbs = []
        for o in self.orbs:
            o[0] += o[2] * dt
            o[1] += o[3] * dt
            ux, uy = o[2] / lv["speed"], o[3] / lv["speed"]
            if mz.wall_at(o[0] + ux * ORB_R / 2, o[1] + uy * ORB_R / 2):
                self.burst(o[0], o[1], ORB, 4)
                continue
            if math.hypot(o[0] - h.x, o[1] - h.y) < ORB_R + CR - 2:
                self.burst(o[0], o[1], ORB, 10)
                if h.shield <= 0 and self.hurt():
                    return  # lost a life: the level was reset (or the run ended)
                continue
            orbs.append(o)
        self.orbs = orbs

        shots = []
        for s in self.shots:
            s.x += s.vx * dt
            s.y += s.vy * dt
            if mz.wall_at(s.x, s.y):
                self.burst(s.x, s.y, h.c["color"], 3)
                continue
            blocked = next((o for o in self.orbs
                            if math.hypot(o[0] - s.x, o[1] - s.y) < s.r + ORB_R), None)
            if blocked:
                self.orbs.remove(blocked)
                self.burst(s.x, s.y, ORB, 10)
                self.sounds.play("block")
                continue
            shots.append(s)
        self.shots = shots

        if math.hypot(h.x - mz.exit[0], h.y - mz.exit[1]) < 22:
            self.level += 1
            if self.level >= len(LEVELS):
                self.level -= 1
                self.state, self.won = "end", True
                self.sounds.play("win")
            else:
                self.start_level()

    def hurt(self):
        """Orb hit the hero. Returns True if it cost a life."""
        h = self.hero
        h.hp -= ORB_DMG
        h.flash = 0.12
        self.shake = 0.12
        self.sounds.play("hit")
        if h.hp > 0:
            return False
        h.lives -= 1
        self.burst(h.x, h.y, h.c["color"], 30)
        self.sounds.play("ko")
        if h.lives <= 0:
            h.hp = 0
            self.state, self.won = "end", False
        else:
            self.start_level()
        return True

    def update_fight(self, dt, keys):
        if self.freeze > 0:
            self.freeze -= dt
            return

        for p in self.players:
            p.update(dt, keys)
            if p.wants_fire(keys) and p.cool <= 0:
                p.cool = p.c["cd"]
                self.shots.append(Shot(p))
                self.sounds.play(f"shoot{p.idx}")

        alive = []
        for s in self.shots:
            s.x += s.vx * dt
            s.y += s.vy * dt
            if not ARENA.collidepoint(s.x, s.y):
                continue
            target = self.players[1 - s.owner.num]
            if math.hypot(s.x - target.x, s.y - target.y) < s.r + RADIUS:
                self.burst(s.x, s.y, s.owner.c["color"], 8)
                if target.shield <= 0:
                    self.hit(target, s)
                continue
            alive.append(s)
        self.shots = alive

    def hit(self, target, shot):
        target.hp -= shot.dmg
        target.flash = 0.12
        n = math.hypot(shot.vx, shot.vy) or 1
        target.x += shot.vx / n * shot.dmg * 0.8
        target.y += shot.vy / n * shot.dmg * 0.8
        self.shake = 0.12
        self.sounds.play("hit")
        if target.hp <= 0:
            target.lives -= 1
            self.burst(target.x, target.y, target.c["color"], 30)
            self.shots = []
            if target.lives <= 0:
                target.hp = 0
                self.winner = 1 - target.num
                self.state = "over"
                self.sounds.play("win")
            else:
                self.sounds.play("ko")
                for p in self.players:
                    p.spawn()
                self.freeze = 1.0

    def burst(self, x, y, color, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(60, 320)
            self.sparks.append([x, y, math.cos(a) * v, math.sin(a) * v,
                                random.uniform(0.2, 0.5), color])

    # ---- rendering ----
    def text(self, surf, s, font, color, pos, anchor="center"):
        img = font.render(s, True, color)
        rect = img.get_rect(**{anchor: pos})
        surf.blit(img, rect)

    def draw(self, surf):
        surf.fill(BG)
        if self.state == "menu":
            self.draw_menu(surf)
        elif self.state == "select":
            self.draw_select(surf)
        elif self.state in ("maze", "end"):
            self.draw_maze(surf)
        else:
            self.draw_fight(surf)

    def draw_menu(self, surf):
        self.text(surf, "CREATURE CLASH", self.big, WHITE, (W // 2, 90))
        for i in range(6):
            draw_creature(surf, i, W // 2 - 250 + i * 100, 200, (0, 1), self.t + i, 1.2)
        options = (("VERSUS", "Two players battle in the arena"),
                   ("CAMPAIGN", "One creature, three mazes, dodge or shoot the orbs"))
        for i, (title, sub) in enumerate(options):
            r = pygame.Rect(W // 2 - 280, 290 + i * 110, 560, 90)
            pygame.draw.rect(surf, FLOOR, r, border_radius=12)
            if self.menu == i:
                pygame.draw.rect(surf, P_COLORS[i], r.inflate(6, 6), 4, border_radius=14)
            self.text(surf, title, self.font, WHITE if self.menu == i else DIM,
                      (r.centerx, r.y + 30))
            self.text(surf, sub, self.small, DIM, (r.centerx, r.y + 60))
        self.text(surf, "W / S or I / K to choose  -  either ALT to confirm  -  Esc to quit",
                  self.small, DIM, (W // 2, 560))

    def hud(self, surf, p, left=True):
        bw = 330
        bx = 30 if left else W - 30 - bw
        self.text(surf, f'P{p.num + 1}  {p.c["name"]}', self.font, P_COLORS[p.num],
                  (bx, 16) if left else (bx + bw, 16), "topleft" if left else "topright")
        pygame.draw.rect(surf, (60, 30, 36), (bx, 46, bw, 20), border_radius=6)
        frac = max(0.0, p.hp / p.c["hp"])
        fill = (90, 210, 110) if frac > 0.5 else (240, 200, 70) if frac > 0.25 else RED
        fw = bw * frac
        pygame.draw.rect(surf, fill, (bx if left else bx + bw - fw, 46, fw, 20),
                         border_radius=6)
        pygame.draw.rect(surf, WHITE, (bx, 46, bw, 20), 2, border_radius=6)
        for i in range(MAX_LIVES):
            hx = bx + 12 + i * 28 if left else bx + bw - 12 - i * 28
            color = RED if i < p.lives else (70, 74, 90)
            pygame.draw.circle(surf, color, (hx - 5, 84), 7)
            pygame.draw.circle(surf, color, (hx + 5, 84), 7)
            pygame.draw.polygon(surf, color, [(hx - 12, 87), (hx + 12, 87), (hx, 100)])

    def draw_maze(self, surf):
        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-4, 4), random.randint(-4, 4)
        mz, h, lv = self.maze, self.hero, LEVELS[self.level]
        pygame.draw.rect(surf, FLOOR, ARENA.move(ox, oy))
        for cy, row in enumerate(mz.rows):
            for cx, ch in enumerate(row):
                r = pygame.Rect(ARENA.left + cx * TILE + ox, ARENA.top + cy * TILE + oy,
                                TILE, TILE)
                if ch == "#":
                    pygame.draw.rect(surf, WALL, r.inflate(-2, -2), border_radius=6)
                elif ch in DIRS:
                    pygame.draw.rect(surf, (62, 44, 84), r.inflate(-2, -2), border_radius=6)
        for (tx, ty, dx, dy), timer in zip(mz.turrets, self.timers):
            charge = 1 - max(0.0, min(1.0, timer / lv["every"]))
            pygame.draw.circle(surf, ORB, (tx + dx * 16 + ox, ty + dy * 16 + oy),
                               5 + 7 * charge)
        ex, ey = mz.exit[0] + ox, mz.exit[1] + oy
        pygame.draw.polygon(surf, (90, 230, 140),
                            poly_points(ex, ey, 20 + 3 * math.sin(self.t * 5), 9, 5,
                                        self.t * 1.5))
        self.text(surf, "EXIT", self.small, WHITE, (ex, ey - 22))

        for s in self.shots:
            draw_shot(surf, h.idx, s.x + ox, s.y + oy, s.r, self.t)
        for o in self.orbs:
            pulse = 1.5 * math.sin(self.t * 10 + o[0] * 0.05)
            pygame.draw.circle(surf, ORB, (o[0] + ox, o[1] + oy), ORB_R + pulse)
            pygame.draw.circle(surf, (245, 200, 255), (o[0] + ox, o[1] + oy), ORB_R * 0.45)
        visible = not (h.shield > 0 and int(self.t * 12) % 2 == 0)
        if self.state == "maze" and visible:
            draw_creature(surf, h.idx, h.x + ox, h.y + oy, h.facing, self.t,
                          CR / RADIUS, h.flash > 0)
        for x, y, _, _, life, color in self.sparks:
            pygame.draw.circle(surf, color, (x + ox, y + oy), 2 + life * 6)

        self.hud(surf, h)
        self.text(surf, f'LEVEL {self.level + 1}/{len(LEVELS)}  {lv["name"]}', self.font,
                  WHITE, (W - 30, 16), "topright")
        self.text(surf, "Reach the EXIT. Shoot the orbs or step out of their way.",
                  self.small, DIM, (W - 30, 50), "topright")
        self.text(surf, "Move: WASD / IJKL   Attack: either ALT", self.small, DIM,
                  (W - 30, 74), "topright")

        if self.state == "end":
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            surf.blit(shade, (0, 0))
            self.text(surf, "CAMPAIGN CLEARED!" if self.won else "GAME OVER", self.big,
                      (90, 230, 140) if self.won else RED, (W // 2, H // 2 - 90))
            if self.won:
                draw_creature(surf, h.idx, W // 2, H // 2 + 10, (0, 1), self.t, 2.2)
            self.text(surf, "Press R to return to the menu", self.font, WHITE,
                      (W // 2, H // 2 + 110))
        elif self.freeze > 0:
            self.text(surf, f"LEVEL {self.level + 1}", self.big, WHITE,
                      (W // 2, ARENA.centery))

    def draw_select(self, surf):
        campaign = self.mode == "campaign"
        self.text(surf, "CHOOSE YOUR CREATURE" if campaign else "CREATURE CLASH",
                  self.big, WHITE, (W // 2, 50))
        self.text(surf, "W A S D or I J K L to choose, either ALT to lock in" if campaign
                  else "P1: W A S D to choose, LEFT ALT to lock in      "
                       "P2: I J K L to choose, RIGHT ALT to lock in",
                  self.small, DIM, (W // 2, 96))
        cw, ch = 250, 205
        x0, y0 = (W - 3 * cw - 40) // 2, 125
        for i, c in enumerate(CREATURES):
            r = pygame.Rect(x0 + (i % 3) * (cw + 20), y0 + (i // 3) * (ch + 20), cw, ch)
            pygame.draw.rect(surf, FLOOR, r, border_radius=12)
            draw_creature(surf, i, r.centerx, r.y + 62, (0, 1), self.t + i, 1.25)
            self.text(surf, c["name"], self.font, WHITE, (r.centerx, r.y + 116))
            self.text(surf, f'{c["type"]} - {c["attack"]}', self.small, c["color"],
                      (r.centerx, r.y + 138))
            stats = (("HP", c["hp"] / 150), ("SPD", c["speed"] / 300),
                     ("POW", c["dmg"] / 26), ("RATE", 0.24 / c["cd"]))
            for j, (label, v) in enumerate(stats):
                bx = r.x + 16 + (j % 2) * 118
                by = r.y + 158 + (j // 2) * 20
                self.text(surf, label, self.small, DIM, (bx, by), "topleft")
                pygame.draw.rect(surf, BG, (bx + 40, by + 4, 64, 8), border_radius=4)
                pygame.draw.rect(surf, c["color"], (bx + 40, by + 4, 64 * v, 8),
                                 border_radius=4)
            for p in ((0,) if campaign else (0, 1)):
                if self.cursor[p] == i:
                    grow = 4 + p * 6
                    width = 6 if self.locked[p] else 3
                    pygame.draw.rect(surf, P_COLORS[p], r.inflate(grow, grow), width,
                                     border_radius=14)
                    tag = f"P{p + 1}" + (" READY" if self.locked[p] else "")
                    self.text(surf, tag, self.small, P_COLORS[p],
                              (r.x + 10, r.y + 8) if p == 0 else (r.right - 10, r.y + 8),
                              "topleft" if p == 0 else "topright")

    def draw_fight(self, surf):
        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-4, 4), random.randint(-4, 4)
        arena = ARENA.move(ox, oy)
        pygame.draw.rect(surf, FLOOR, arena, border_radius=14)
        for gx in range(arena.left + 60, arena.right, 60):
            pygame.draw.line(surf, FLOOR_LINE, (gx, arena.top + 8), (gx, arena.bottom - 8))
        for gy in range(arena.top + 60, arena.bottom, 60):
            pygame.draw.line(surf, FLOOR_LINE, (arena.left + 8, gy), (arena.right - 8, gy))
        pygame.draw.rect(surf, FLOOR_LINE, arena, 3, border_radius=14)

        for s in self.shots:
            draw_shot(surf, s.owner.idx, s.x + ox, s.y + oy, s.r, self.t)
        for p in self.players:
            if self.state == "over" and p.num != self.winner:
                continue
            if p.shield > 0 and int(self.t * 12) % 2 == 0 and self.state == "fight":
                continue  # blink while invulnerable
            draw_creature(surf, p.idx, p.x + ox, p.y + oy, p.facing, self.t,
                          flash=p.flash > 0)
            self.text(surf, f"P{p.num + 1}", self.small, P_COLORS[p.num],
                      (p.x + ox, p.y + oy - RADIUS * 1.9))
        for x, y, _, _, life, color in self.sparks:
            pygame.draw.circle(surf, color, (x + ox, y + oy), 2 + life * 6)

        # HUD
        for p in self.players:
            self.hud(surf, p, p.num == 0)
        self.text(surf, "VS", self.font, DIM, (W // 2, 56))

        if self.state == "over":
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 130))
            surf.blit(shade, (0, 0))
            win = self.players[self.winner]
            self.text(surf, f"PLAYER {self.winner + 1} WINS!", self.big,
                      P_COLORS[self.winner], (W // 2, H // 2 - 90))
            draw_creature(surf, win.idx, W // 2, H // 2 + 10, (0, 1), self.t, 2.2)
            self.text(surf, "Press R to return to the menu", self.font, WHITE,
                      (W // 2, H // 2 + 110))
        elif self.freeze > 0:
            self.text(surf, "READY..." if self.freeze > 0.35 else "FIGHT!", self.big,
                      WHITE, (W // 2, ARENA.centery))


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Creature Clash")
    clock = pygame.time.Clock()
    game = Game()
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if game.state == "menu":
                        running = False
                    else:
                        game.to_menu()
                else:
                    game.keydown(e.key)
        game.update(dt, pygame.key.get_pressed())
        game.draw(screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
