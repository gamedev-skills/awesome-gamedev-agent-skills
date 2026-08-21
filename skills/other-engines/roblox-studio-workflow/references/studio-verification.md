# Roblox Studio verification evidence

Read this before claiming a change was tested in Studio.

## Select modes by risk

- **Run**: server/world behavior without a player.
- **Play / Play Here**: quick integrated player path or spawn-location context.
- **Server & Clients**: separate server and up to multiple clients; required for meaningful remote,
  ownership, targeted replication, join/leave, and simultaneous-player checks.
- **Device Emulator**: resolutions, orientation, DPI/device constraints, touch simulation, and
  streaming behavior under representative device conditions.
- **Controller Emulator**: input mappings and gamepad UI navigation.
- **Studio-only scripted testing services**: automation where the installed Studio/API and project
  tooling expose observable results; do not invent a headless workflow.

## Evidence record

For each run record Studio version/date, place/build source, mode, client count, emulated device or
controller, setup, action, expected result, observed result, relevant server/client Output, and
pass/fail. Screenshots help visual review but do not replace interaction or Output evidence.

Separate verification levels explicitly:

- **Executed:** observed in a running Studio session with Output/result evidence.
- **Statically checked:** parsed, linted, type-checked, or inspected without engine execution.
- **Prepared, not run:** an exact scenario/harness exists but requires manual Studio interaction.
- **Unverified:** no adequate check was possible.

Never collapse the latter three into “Studio tested.”

## Temporary harness rules

Keep a harness isolated and easy to remove. It may expose a pure validator or create representative
instances, but must call the production boundary rather than reimplement it. Guard Studio-only
fixtures so they cannot run in a published server. Remove test remotes, Parts, scripts, tags,
Attributes, debug UI, and logs before final hierarchy review.

## UI quality scenario

For an inventory/HUD/settings evaluation, author a real `ScreenGui` hierarchy with header, primary
content, secondary detail, repeated-item template, and action/footer region. Populate empty, small,
and overflow datasets. Verify desktop, narrow portrait, mobile landscape, tablet-like, and console;
mouse hover/press, touch activation, gamepad focus and scroll-follow; safe insets; long text;
disabled/error state; open/close interruption; respawn/reset policy; and Explorer readability.

Reject and revise if visual hierarchy depends on universal rounded cards, random gradients/neon,
oversized headings, excessive empty space/transparency/blur, identical action hierarchy, or noisy
motion. Fix the skill guidance—not only the fixture—when the output followed an underspecified rule.

## Networking scenario

Use at least two clients for valid, malformed, spam, out-of-range, stale character, leave during
work, rapid respawn, simultaneous requests, targeted response, and broadcast. Check authoritative
state in server context and visibility in every client, plus limiter/cleanup state after leave.

## Primary reference

- `https://create.roblox.com/docs/studio/testing-modes`
