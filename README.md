# Creature Clash

A fast-paced, elemental monster battle game built with Python and Pygame. Choose from six unique creatures and battle opponents in the arena or navigate through three challenging mazes.

## Game Modes

- **Versus**: Two players battle in an arena with real-time combat
- **Campaign**: Solo adventure through three progressively difficult mazes while dodging turret orbs and reaching the exit

## Controls

**Player 1**: `W` `A` `S` `D` (move), `Left Alt` or `Q` (attack)  
**Player 2**: `I` `J` `K` `L` (move), `Right Alt` or `O` (attack)  
**Menu**: `Esc` (return to menu)

## Running the Game

```bash
uv run main.py
```

---

# Code Architecture

The game is organized into distinct layers: **sound synthesis**, **drawing functions**, **game objects**, and **game state management**.

## Overview of Classes

### Core Game Classes

#### `Sounds`
Synthesizes audio effects programmatically without asset files. Generates tones, square waves, and noise patterns for sound effects like attacks, hits, and victories.

**Key Methods:**
- `__init__()`: Initializes Pygame mixer and generates all sound effects
- `play(name)`: Plays a sound by name

---

#### `Player`
Represents a player-controlled creature in versus mode.

**Key Attributes:**
- `x, y`: Position in the arena
- `hp`: Current health points
- `facing`: Direction vector (normalized)
- `cool`: Cooldown timer for attacks
- `flash`: Visual flash effect timer
- `shield`: Invulnerability timer after spawning
- `idx`: Creature type index (0-5)
- `num`: Player number (0 or 1)

**Key Methods:**
- `spawn()`: Resets position, health, and state
- `update(dt, keys)`: Updates position based on input, respects arena boundaries
- `wants_fire(keys)`: Returns `True` if the player pressed an attack key

---

#### `Shot`
Represents a projectile fired by a player or hero.

**Key Attributes:**
- `x, y`: Current position
- `vx, vy`: Velocity components
- `r`: Radius for collision detection
- `dmg`: Damage value
- `owner`: Reference to the creature that fired it

---

#### `Hero(Player)`
A single creature for campaign mode. Extends `Player` to accept input from either player's keys.

**Key Methods:**
- `place(x, y)`: Positions the hero at the given coordinates
- `update(dt, keys, maze)`: Updates movement with collision detection against maze walls

---

#### `Maze`
Encapsulates campaign level layout and turret management.

**Key Attributes:**
- `rows`: 2D grid of characters representing the level
- `turrets`: List of turret positions and firing directions
- `start`: Entry point coordinates
- `exit`: Goal coordinates

**Key Methods:**
- `center(cx, cy)`: Converts grid coordinates to pixel coordinates
- `wall(cx, cy)`: Checks if a grid cell is a wall
- `wall_at(x, y)`: Checks if a pixel coordinate overlaps a wall
- `push_out(x, y, r)`: Pushes a circle out of walls it overlaps (collision resolution)

**Map Legend:**
- `'#'` = wall
- `'.'` = floor
- `'S'` = start position
- `'E'` = exit
- `'<', '>', '^', 'v'` = turrets firing in that direction

---

#### `Game`
Central game state manager. Handles all state transitions, input, simulation, and rendering.

**Key Attributes:**
- `state`: Current game state ("menu", "select", "fight", "maze", "over", "end")
- `t`: Global time counter (incremented every frame)
- `sparks`: List of particle effects [x, y, vx, vy, life, color]
- `shake`: Screen shake intensity and timer
- `players`: List of two `Player` objects in versus mode
- `hero`: Single `Hero` for campaign mode
- `maze`: Current `Maze` object
- `shots`: List of active `Shot` objects
- `orbs`: List of active turret orbs (campaign mode)

**Key Methods:**
- `to_menu()`: Transition to main menu
- `to_select(mode)`: Transition to creature selection
- `to_fight()`: Start versus battle
- `start_campaign()`: Initialize campaign run
- `start_level()`: Load a maze level
- `update(dt, keys)`: Main update loop
- `draw(surf)`: Main rendering dispatcher

---

## Drawing Functions

All draw functions accept a Pygame surface and render elements. The game uses procedural drawing—no image assets required.

### `poly_points(cx, cy, r_out, r_in, n, rot=0.0)` → list
Generates vertices for a star-shaped polygon.

**Parameters:**
- `cx, cy`: Center coordinates
- `r_out`: Outer radius
- `r_in`: Inner radius
- `n`: Number of points
- `rot`: Starting rotation angle

**Returns:** List of (x, y) tuples

**Usage:** Used to draw creatures' attack effects and game elements

---

### `draw_creature(surf, idx, x, y, facing=(0, 1), t=0.0, scale=1.0, flash=False)`

Renders a creature sprite procedurally. Each creature has a unique visual design.

**Parameters:**
- `surf`: Pygame surface to draw on
- `idx`: Creature type (0-5)
- `x, y`: Position
- `facing`: Direction vector (normalized) for eye orientation
- `t`: Time parameter for animation
- `scale`: Size multiplier
- `flash`: Whether to render in white (hit/shield effect)

**Creature Designs:**

| Index | Name | Design |
|-------|------|--------|
| 0 | Mossling | Round green body with leaf protrusions |
| 1 | Voltuft | Spiky electric star that rotates |
| 2 | Cinderpup | Orange body with animated flame crests |
| 3 | Bubblefin | Blue creature with side fins and tail wag |
| 4 | Pebblor | Gray boulder with crystal spikes |
| 5 | Fluffkin | Puffball with round ears and floating body rings |

**Features:**
- **Shadow**: Ellipse under each creature
- **Bob animation**: Y position oscillates using `sin(t * 6)` for a floating effect
- **Eyes**: Follow the facing direction
- **Idle animation**: Each creature has frame-based movement (fin wag, flame flicker, rotation, etc.)

---

### `draw_shot(surf, idx, x, y, r, t)`

Renders a projectile specific to the attacking creature's type.

**Parameters:**
- `surf`: Pygame surface
- `idx`: Creature type (determines appearance)
- `x, y`: Position
- `r`: Radius
- `t`: Time for animation

**Shot Designs:**

| Creature | Appearance |
|----------|------------|
| Bubblefin (3) | Outlined circle with accent dot |
| Voltuft (1), Fluffkin (5) | Rotating star polygon |
| Pebblor (4) | Rotating square |
| Mossling (0) | Double-leaf shape |
| Cinderpup (2), others | Solid circle with accent ring |

---

## Rendering Pipeline

The draw system follows this order:

### Game State Dispatch (`Game.draw(surf)`)
Routes to the appropriate draw function based on current state.

```
Menu → draw_menu()
Select → draw_select()
Fight → draw_fight()
Maze/End → draw_maze()
```

---

### Draw Functions by Game State

#### `draw_menu(surf)`
**Renders:**
1. Title
2. All 6 creatures as carousel
3. Two menu options (Versus/Campaign) with descriptions
4. Control instructions

---

#### `draw_select(surf)`
**Renders:**
1. Creature selection grid (3x2)
2. Each creature with:
   - Preview (larger scale)
   - Name and type
   - Attack name
   - Four stat bars (HP, SPD, POW, RATE)
   - Selection border (different colors for P1/P2)
   - "READY" tag if locked in

---

#### `draw_fight(surf)`
**Rendering Order:**
1. **Arena floor**: Gray rectangle with grid lines
2. **Projectiles**: Call `draw_shot()` for each active shot
3. **Players**: Call `draw_creature()` for each player
   - Hidden during spawn invulnerability (blinking)
   - P1/P2 label above each
4. **Particle effects**: Render all sparks
5. **HUD**: Health bars, lives, player labels (left/right)
6. **Overlay**: "READY... FIGHT!" countdown or victory screen

**Screen Shake:** Random `ox, oy` offsets applied to all drawn objects when collision damage occurs

---

#### `draw_maze(surf)`
**Rendering Order:**
1. **Floor**: Gray background
2. **Walls**: Rounded rectangles with slight inset
3. **Turret positions**: Circles with charging animation (size grows as fire timer counts down)
4. **Exit**: Pulsing star polygon with "EXIT" label
5. **Shots**: Player projectiles with `draw_shot()`
6. **Orbs**: Turret projectiles with pulsing outline
7. **Hero**: Call `draw_creature()` with smaller scale
   - Blinks during invulnerability
8. **Particle effects**: Render all sparks
9. **HUD**: Hero health, level/maze name, control instructions
10. **End screen**: Overlay with "CLEARED!" or "GAME OVER", victory creature, restart prompt

**Screen Shake:** Applied to all maze elements during collision

---

#### `draw_select(surf)`
(Same as creature selection screen)

---

### Helper Drawing Functions

#### `Game.text(surf, s, font, color, pos, anchor="center")`
Renders text with anchor positioning (topleft, topright, center, etc.)

#### `Game.hud(surf, p, left=True)`
Renders player HUD:
- Player name and creature type
- Health bar (green → yellow → red based on HP %)
- Lives indicator (pulsing circles and triangle shape)

---

## Animation Timing

Animations use `self.t` (global time in seconds) with trigonometric functions:

- **Creature bob**: `sin(t * 6) * 2` (up/down oscillation)
- **Star rotation**: `t * 3` or similar (spinning)
- **Fin wag**: `sin(t * 8) * R * 0.2` (swinging motion)
- **Flame flicker**: `sin(t * 14 + offset)` (high-frequency oscillation)
- **Exit pulse**: `sin(t * 5)` (size expansion)
- **Blinking**: `int(t * 12) % 2 == 0` (alternates every 12 cycles per second)

---

## Game Loop

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    game = Game()
    
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        
        # Input
        for event in pygame.event.get():
            game.keydown(key)
        
        # Simulation
        game.update(dt, pygame.key.get_pressed())
        
        # Rendering
        game.draw(screen)
        pygame.display.flip()
```

**Frame Rate:** 60 FPS  
**Delta Time Clamp:** 0.05s max (prevents large jumps on slow frames)

---

## Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `W, H` | 960, 620 | Screen resolution |
| `ARENA` | Rect with margin | Playable area |
| `RADIUS` | 26 | Player creature size |
| `MAX_LIVES` | 3 | Lives per player |
| `TILE` | 60 | Maze grid cell size |
| `CR` | 18 | Hero radius in maze (smaller) |
| `ORB_R` | 11 | Turret projectile radius |
| `ORB_DMG` | 25 | Orb damage per hit |

---

## Creature Data

Each creature is defined in the `CREATURES` list with:
- **name**: Display name
- **type**: Elemental type (Grass, Electric, Fire, Water, Rock, Normal)
- **color**: Body color (RGB)
- **accent**: Secondary color for details
- **attack**: Attack name
- **hp**: Max health
- **speed**: Movement pixels/second
- **dmg**: Damage per hit
- **shot**: Projectile speed pixels/second
- **cd**: Cooldown in seconds
- **r**: Projectile radius

---

## Summary

The code uses **procedural drawing** to render all visuals, with animation driven by a global time variable. The **Game class** orchestrates all systems: input handling, physics simulation, collision detection, and rendering. Each draw function manages a logical layer of the UI/game world, maintaining separation of concerns and making it easy to add or modify visual elements.
