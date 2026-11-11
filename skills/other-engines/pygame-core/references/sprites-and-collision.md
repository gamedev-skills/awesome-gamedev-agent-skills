# pygame sprites, collision & media (pygame-ce 2.5+)

Depth behind the pygame-core skill: group variants, pixel-perfect collision,
spritesheets, animation, and audio/text.

## Contents

- [Group variants](#group-variants): `GroupSingle`, `LayeredUpdates`, `RenderUpdates`
- [Collision functions](#collision-functions): rect, circle, ratio and "any" tests
- [Pixel-perfect collision with masks](#pixel-perfect-collision-with-masks)
- [Slicing a spritesheet](#slicing-a-spritesheet) and
  [simple frame animation](#simple-frame-animation)
- [Audio](#audio) and [text](#text)

## Group variants

`pygame.sprite` ships several containers; pick by need:

| Class | Use for |
|-------|---------|
| `Group` | the general case; `update(*args)` + `draw(surface)` |
| `GroupSingle` | a slot holding at most one sprite (e.g. the player) |
| `LayeredUpdates` | groups that draw by a per-sprite `_layer` (z-order) |
| `RenderUpdates` | tracks dirty rects for partial-screen redraws |

```python
from pygame.sprite import LayeredUpdates
world = LayeredUpdates()
world.add(background, layer=0)
world.add(player, layer=10)        # higher layer draws on top
world.add(ui, layer=20)
world.update(dt)
world.draw(screen)
```

A sprite removes itself from **all** groups with `self.kill()`. Membership is
two-way: `group.has(sprite)`, `sprite.groups()`.

## Collision functions

`spritecollide` and `groupcollide` use rect overlap by default. The optional
`collided` callback swaps in a more precise test:

```python
import pygame
from pygame.sprite import collide_rect, collide_circle, collide_mask

# Circle collision (set sprite.radius, or it's derived from the rect):
pygame.sprite.spritecollide(player, rocks, False, collide_circle)

# Pixel-perfect via masks (see below):
pygame.sprite.spritecollide(player, spikes, False, collide_mask)
```

Other helpers: `pygame.sprite.collide_rect_ratio(0.75)` (shrunken rect),
`spritecollideany` (fast boolean-ish "any hit"), and `Rect` methods
`colliderect`, `collidepoint`, `collidelist`, `collidelistall`.

## Pixel-perfect collision with masks

Rect collision is generous; for tight hitboxes build a `Mask` from each sprite's
alpha and test overlap:

```python
class Bullet(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        super().__init__()
        self.image = image.convert_alpha()
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)  # build once

# collide_mask uses each sprite's .mask:
if pygame.sprite.collide_mask(bullet, enemy):
    enemy.kill()
```

Rebuild the mask if the sprite's image changes (e.g. each animation frame), or
keep a per-frame list of masks.

## Slicing a spritesheet

```python
def load_frames(path, frame_w, frame_h):
    sheet = pygame.image.load(path).convert_alpha()
    cols = sheet.get_width() // frame_w
    rows = sheet.get_height() // frame_h
    frames = []
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
            frames.append(sheet.subsurface(rect))   # view into the sheet, no copy
    return frames
```

## Simple frame animation

```python
class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, frames, fps, pos):
        super().__init__()
        self.frames = frames
        self.frame_time = 1 / fps
        self.timer = 0.0
        self.index = 0
        self.image = frames[0]
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.index = (self.index + 1) % len(self.frames)
            self.image = self.frames[self.index]
```

## Audio

```python
pygame.mixer.init()                       # or rely on pygame.init()
jump_sfx = pygame.mixer.Sound("jump.wav") # short SFX, fully loaded
jump_sfx.set_volume(0.5)
jump_sfx.play()

pygame.mixer.music.load("theme.ogg")      # streamed music (one track at a time)
pygame.mixer.music.set_volume(0.3)
pygame.mixer.music.play(loops=-1)         # -1 = loop forever
```

Prefer `.ogg`/`.wav`; keep many short effects as `Sound`, and long tracks on the
single `music` stream.

## Text

```python
font = pygame.font.Font(None, 36)         # None = default font; or a .ttf path
# Antialiased text is slow to render — cache the Surface, re-render only on change.
label = font.render(f"Score: {score}", True, (255, 255, 255))
screen.blit(label, (10, 10))
```

Re-rendering text every frame is a common performance trap; render once and re-blit,
re-rendering only when the string changes.
