# Input buffering, game feel, devices, and accessibility

The action layer makes controls work; these refinements make them feel good and
reach more players.

## Buffering and coyote time, tuned

Both convert "I pressed it at almost the right moment" into success:

- **Input buffer** — when an action is pressed but can't fire yet (mid-air jump,
  attack during recovery), remember it for a short window and fire the instant it
  becomes valid. Typical window: ~100–150 ms (≈6–9 frames at 60 Hz).
- **Coyote time** — allow a ground action (jump) for a brief window *after*
  leaving the ledge. Typical window: ~80–120 ms. Players perceive the edge as
  generous, not buggy.

Tuning notes:

- Express windows in **seconds**, not frames, so they're frame-rate independent.
- **Consume** the buffer when it fires, and reset coyote on a successful jump, so
  one press = one action (no double jumps from a lingering buffer).
- Too-long windows feel mushy or cause unintended actions; too-short feel
  punishing. Tune by playtest, per game.

## Jump feel (where input meets physics)

Input handling and `physics-tuning` together create jump feel:

- **Variable height**: full gravity while rising only if the button is held; if
  released early, increase downward acceleration (or cut upward velocity) so a tap
  is a short hop. Read the *held* state for this, the *edge* for the initial jump.
- **Apex hang**: reduce gravity near the top of the arc for a brief float — gives
  air control and reads as responsive.
- **Fast fall / increased fall gravity**: heavier gravity on the way down than up
  makes jumps feel snappy rather than floaty.

These are physics tweaks driven by input state; keep the input layer reporting
edge/held cleanly so the controller can apply them.

## Device detection and prompt swapping

- Track the **last-used device**: when an event arrives, note whether it was
  keyboard/mouse, a specific gamepad type, or touch. Switch on-screen button
  glyphs and tutorials to match.
- Don't assume a single gamepad layout — Xbox, PlayStation, and Switch differ in
  face-button labels. Map to abstract **positions** (South/East/West/North) and
  pick the icon set per controller. SDL3 names buttons this way
  (`SDL_GAMEPAD_BUTTON_SOUTH`…, with `SDL_GetGamepadButtonLabel` and
  `SDL_GetGamepadType` for the printed label and family), and so does Godot 4.7,
  whose desktop joypad driver is SDL3: `JOY_BUTTON_A` is the bottom button —
  Xbox A, PlayStation Cross, Nintendo B. Read the family from
  `Input.get_joy_name()` / `Input.get_joy_info()` (vendor and product IDs).
- **Steam Input** may sit between the pad and your game: when it is on for a
  controller, the game sees an emulated Xbox-style pad, so name and ID checks
  report Xbox even for a PlayStation or Switch pad and you show the wrong
  glyphs. Ask Steam for the real type (`ISteamInput::GetControllerForGamepadIndex`
  + `GetInputTypeForHandle`; Godot exposes the index as `steam_input_index` in
  `get_joy_info()`), or fetch Steam's own art (`GetGlyphPNGForActionOrigin` /
  `GetGlyphSVGForActionOrigin`).
- Godot 4.7's SDL3 joypad driver covers Windows, Linux, macOS and (new in 4.7) iOS;
  on Android and Web `get_joy_info()` is empty, so fall back to `get_joy_name()` there.
- Support **hot-swapping**: a player may start on keyboard and pick up a
  controller mid-session. Re-resolve prompts on device change without a restart.

## Touch controls

- Provide on-screen controls sized for thumbs (virtual stick / buttons) or
  gesture mappings, routed through the **same action layer** as physical input.
- A virtual stick should use a **floating origin** (anchor where the thumb lands)
  and a radial deadzone, just like a physical stick.
- Avoid relying on precise multi-touch chords; offer larger hit areas and
  forgiving timing. Test on a range of screen sizes.

## Accessibility checklist

Input is one of the highest-impact accessibility surfaces. Aim for:

- **Full remapping** of every action, for every device, with conflict detection
  and reset-to-default.
- **Toggle vs hold** options for actions that default to hold (aim, crouch,
  sprint) — sustained presses are painful or impossible for some players.
- **No required simultaneous inputs** for essential actions; offer single-input
  alternatives or sequential equivalents.
- **Adjustable sensitivity and deadzone** for sticks and aim, plus optional
  aim assist.
- **Adjustable timing windows** where feasible (extend buffer/coyote, slow QTEs),
  or a "hold instead of mash" option for repeated-press prompts.
- **Stick/axis inversion** (X and Y independently) for camera and movement.
- **Input latency**: process discrete presses promptly and avoid adding
  artificial delay; perceived lag harms both feel and accessibility.

## Loop placement

- Read **held/axis** state in the fixed/physics step so movement is consistent
  with the simulation (see `physics-tuning`).
- Capture **discrete presses** as events (or via a just-pressed flag latched each
  frame) so a press between physics ticks is never lost.
- Save custom bindings and input settings through `save-systems` and reload them
  at startup before the first frame of gameplay.
