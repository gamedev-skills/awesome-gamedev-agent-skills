---
name: pygame-core
description: >
  Builds and debugs 2D games in Python with pygame-ce (imported as pygame): the event-update-draw
  loop, delta time, Surfaces and Rects, Sprite groups and headless tests. Use when code imports
  pygame, or a window says not responding, speed differs per PC or pygame and pygame-ce conflict.
  Not for engine-neutral input or saves (`input-systems`, `save-systems`) or jump feel
  (`platformer`).
---

# pygame Core

Build and debug a pygame game. New code targets **pygame-ce 2.5.8**, the maintained
community fork; it installs as `pygame-ce` and imports as `pygame`. Legacy `pygame` 2.6
code mostly runs unchanged; pygame-ce-only APIs such as `FRect` and `get_frect()` need the
fork, which `getattr(pygame, "IS_CE", False)` detects.

## When to use

- Starting a pygame game, or fixing its loop, speed, input, drawing, sprite groups,
  collision, audio or text.
- Any project with `import pygame`, whichever package provides it.

**When not to use:** Python questions unrelated to pygame; 3D; portable design work owned by
the related skills below.

## Workflow

1. **Check the install.** `python -c "import pygame; print(pygame.version.ver,
   getattr(pygame, 'IS_CE', False))"`. Keep the project's package; for a new project use
   `pip install pygame-ce`.
2. **Keep logic testable.** Put rules in classes or functions that take `dt` and an input
   snapshot, so a test can drive them without a window. Only the loop touches the display.
3. **One loop per frame:** drain events, update with a clamped `dt`, draw, `flip()`. Use
   pixels per second, and float positions (`FRect` or `Vector2`).
4. **Load assets after `set_mode`**, then `convert()` / `convert_alpha()` once each.
5. **Verify headless.** Run the tests and a short scripted run with the dummy drivers (see
   the check below), then open the saved PNG. Report what ran. Feel, audio and real input
   still need a person: ask the user to play for a minute and report speed, controls and
   sound.

## Pattern: a loop that can run headless

```python
import argparse
import pygame

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=0, help="quit after N frames (0 = run)")
    ap.add_argument("--shot", help="save the last frame to this PNG")
    args = ap.parse_args(argv)

    pygame.init()
    screen = pygame.display.set_mode((320, 180), pygame.SCALED)  # before any convert()
    clock = pygame.time.Clock()
    sprites = pygame.sprite.Group(Player((160, 90)))

    frame, running = 0, True
    while running:
        dt = min(clock.tick(60) / 1000, 0.05)          # clamp stalls (window drag, debugger)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        sprites.update(dt, pygame.key.get_pressed())
        screen.fill((18, 18, 28))
        sprites.draw(screen)
        pygame.display.flip()
        frame += 1
        if args.frames and frame >= args.frames:
            if args.shot:
                pygame.image.save(screen, args.shot)
            running = False
    pygame.quit()
```

```python
class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.image.load("player.png").convert_alpha()
        self.rect = self.image.get_frect(center=pos)   # FRect keeps sub-pixel positions
        self.speed = 120                               # pixels per second

    def update(self, dt, keys):
        move = pygame.Vector2(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT],
                              keys[pygame.K_DOWN] - keys[pygame.K_UP])
        if move.length_squared():                      # zero vectors cannot be scaled
            move.scale_to_length(self.speed * dt)      # same speed on diagonals
        self.rect.center += move
```

Use `KEYDOWN` / `MOUSEBUTTONDOWN` events for one-off actions (jump, pause, click) and
`key.get_pressed()` for held movement. `pygame.SCALED` draws a small logical screen into a
larger window (handy for pixel art) and scales mouse events back to logical coordinates;
the docs still call it experimental.

## The check to run

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --frames 120 --shot frame.png
```

A unit test sets the same variables before `import pygame`, calls `pygame.init()` and
`pygame.display.set_mode((1, 1))` in `setUp` (so `convert_alpha()` works), feeds a fake key
snapshot and asserts on positions after a fixed number of `update(1 / 60, keys)` calls. The
PNG has the logical size (320×180 here), not the scaled window size. The dummy run proves
that the loop, loading and drawing work; it cannot show frame pacing or how input feels.

## Gotchas

- **Window freezes or shows "not responding"** → the event queue is not drained every frame.
  Call `pygame.event.get()` (or `pygame.event.pump()`) once per frame, including in menus and
  loading screens.
- **Game runs faster on a faster machine** → movement per frame instead of per second. Scale
  by `dt` from `clock.tick()`.
- **Objects jump or pass through walls after a window drag or a breakpoint** → the next
  `clock.tick()` returns the whole stall. Clamp it: `min(clock.tick(60) / 1000, 0.05)`.
- **Slow movement gets stuck or jitters** → `Rect` stores integers and truncates each
  update (`rect.x += 0.5` never moves). Use `get_frect()` / `FRect` (pygame-ce; groups
  and collision accept it) or keep a `Vector2` position and assign `rect.center` from it.
- **`ValueError: Can't normalize Vector of length zero`** (or `Cannot scale a vector with
  zero length`) → `normalize()` / `scale_to_length()` ran with no keys held. Check
  `length_squared()` first.
- **`pygame.error: No convert format has been set`** → `convert()` / `convert_alpha()` ran
  before `display.set_mode()`. Load images after opening the window.
- **Blits are slow** → images were never converted. Convert each one once at load.
- **`pygame.error: mixer not initialized`** on a server, in CI or on a machine without
  sound → `pygame.init()` does not raise when a module fails; it returns `(passed,
  failed)` and leaves the mixer off. Set `SDL_AUDIODRIVER=dummy` for headless runs, or check
  `pygame.mixer.get_init()` and skip audio.
- **Text rendering eats the frame budget** → `font.render` every frame. Cache the surface
  and re-render only when the string changes.
- **`import pygame` gives the wrong version, or `module 'pygame' has no attribute
  'version'`** → `pygame` and `pygame-ce` were both installed into one environment: they
  share the `pygame` folder, the last install wins, and removing either breaks the other.
  Run `pip uninstall -y pygame pygame-ce`, then `pip install pygame-ce`.
- **Nothing appears** → no `display.flip()`, or `screen.fill()` runs after the drawing.
  Draw back to front: background, world, sprites, HUD.

## References

- Read `references/sprites-and-collision.md` when the game needs more than one `Group`:
  `GroupSingle` and `LayeredUpdates` z-order, circle and mask (pixel-perfect) collision,
  spritesheet slicing, frame animation, sound effects and music, and cached text.

## Related skills

- `input-systems`, `save-systems` — engine-neutral rebinding and persistence.
- `platformer`, `roguelike` — genre rules that bind to this loop.
- `love2d-core` — the same loop in LÖVE; `bevy-ecs` — when a project outgrows pygame.

## Version notes

Last verified: 2026-11-11.

- pygame-ce 2.5.8 (released 2026-08-09) is the latest release; it needs Python 3.10+ and
  ships wheels for CPython 3.10 to 3.15 and PyPy 3.11. It bundles SDL 2.32.10.
- Legacy pygame's latest release is 2.6.1 (2024-09-29).
- The loop, sprite, test and headless commands above, the error texts in Gotchas and the
  pygame/pygame-ce install clash were run with pygame-ce 2.5.8 on Python 3.12 and the SDL
  dummy drivers.
- Sources: [pygame-ce on PyPI](https://pypi.org/project/pygame-ce/),
  [pygame-ce releases](https://github.com/pygame-community/pygame-ce/releases),
  [pygame-ce docs](https://pyga.me/docs/), [pygame on PyPI](https://pypi.org/project/pygame/).
