# Buffer tuning, devices, touch and accessibility

Contents: buffer windows; device detection and button prompts; touch controls; accessibility
checklist; loop placement.

## Buffer windows

A buffer remembers a discrete press that arrived slightly before it became legal (an attack
during recovery, a dodge during a landing, a menu confirm during a transition) and fires it the
moment it is allowed.

- Typical window: 100-200 ms. Combo links in fighting games are often tighter and fixed per
  move; a menu confirm can be longer.
- Express windows in seconds of game time, not frames, so they survive frame-rate changes,
  pause and hit-stop.
- Consume on fire so one press is one action, and clear the buffer on death, scene change and
  cutscenes.
- Too long feels mushy and fires unintended actions; too short feels unresponsive. Expose the
  window as a constant so it can be tuned from playtest reports.
- Jump buffering and coyote time are the same idea applied to the jump controller; `platformer`
  owns them and their numbers.

## Device detection and button prompts

- Track the **last-used device**: when an event arrives, note whether it was keyboard/mouse, a
  gamepad (and which family) or touch, and switch glyphs and tutorial text to match.
- Map buttons to **positions** (South, East, West, North), then pick the icon set per family.
  SDL3 names buttons this way (`SDL_GAMEPAD_BUTTON_SOUTH` and friends, with
  `SDL_GetGamepadButtonLabel` and `SDL_GetGamepadType` for the printed label and family), and
  so does Godot 4.7, whose desktop and iOS joypad driver is SDL3: `JOY_BUTTON_A` is the bottom
  button, which is Xbox A, PlayStation Cross and Nintendo B. Read the family from
  `Input.get_joy_name()` and `Input.get_joy_info()` (vendor and product IDs). On Android and
  Web `get_joy_info()` is empty, so fall back to `get_joy_name()` there.
- **Steam Input** may sit between the pad and the game. When it is on for a controller, the game
  sees an emulated Xbox-style pad, so name and ID checks report Xbox for a PlayStation or Switch
  pad. Ask Steam for the real type (`ISteamInput::GetControllerForGamepadIndex` plus
  `GetInputTypeForHandle`; Godot exposes the index as `steam_input_index` in `get_joy_info()`),
  or fetch Steam's own art (`GetGlyphPNGForActionOrigin` / `GetGlyphSVGForActionOrigin`).
- Support **hot-swapping**: a player may start on keyboard and pick up a pad mid-session.
  Re-resolve prompts on device change without a restart.

## Touch controls

- On-screen controls sized for thumbs (virtual stick and buttons) or gestures, routed through
  the same actions as physical input.
- A virtual stick uses a floating origin (anchored where the thumb lands) and the same radial
  deadzone as a physical stick.
- Avoid precise multi-touch chords; use large hit areas and forgiving timing. Ask the user to
  test on the smallest and largest target screens and report missed or accidental presses.

## Accessibility checklist

- Full remapping of every action for every device, with conflict handling and reset to default.
- Toggle vs hold for actions that default to hold (aim, crouch, sprint).
- No required simultaneous inputs for essential actions; offer single-input or sequential
  alternatives.
- Adjustable stick sensitivity and deadzone, plus optional aim assist.
- Adjustable timing windows where possible (longer buffers, slower quick-time events), and a
  hold option instead of button mashing.
- Independent X and Y inversion for camera and movement.
- No artificial input delay; process discrete presses on the frame or tick they arrive.

## Loop placement

- Read held and axis state in the physics step so movement agrees with the simulation (see
  `physics-tuning`).
- Capture discrete presses as events, or with a just-pressed check in the step that uses them,
  so a press between physics ticks is not lost. Godot's `is_action_just_pressed` still returns
  true for a press that was released again quickly, so a fast tap is not dropped.
- Load saved bindings at startup before the first gameplay frame.
