# Roblox Studio verification evidence

Read this before claiming a change was tested in Studio.

## Select modes by risk

- **Run**: server/world behavior without a player.
- **Test / Test Here**: quick single-session player path or camera-position spawn; toggle the
  Client/Server view while it runs.
- **Server & Clients**: separate server and up to eight clients; required for meaningful remote,
  ownership, targeted replication, join/leave, and simultaneous-player checks.
- **Device Simulator**: resolutions, orientation, DPI and scaling, on-screen keyboard, touch, and
  device switching mid-playtest. It does not simulate device memory or performance; test real
  hardware for that.
- **Controller Emulator**: input mappings and gamepad UI navigation.
- **Network Simulator**: separate inbound and outbound latency, jitter and packet loss on playtest
  connections, with presets for wired, Wi-Fi and mobile; use it for Server Authority prediction and
  `UnreliableRemoteEvent` behavior. It affects Studio playtests only.
- The toolbar versions of Device Simulator and Network Simulator were a Studio beta on 2026-11-11
  (File → Beta Features → *New Device Simulator*, then restart). If the user cannot find them, ask
  whether that beta is on.
- **`TestService`**: Studio-only scripted assertions (`TestService:Check()`, `Require()`,
  `Message()`, `Fail()`) surfaced in the Output/TestService pane. Use it where the installed
  Studio/API and project tooling expose observable results; do not invent a headless workflow.
- **`StudioTestService`** (plugin context): `ExecuteMultiplayerTestAsync(numPlayers, args)`
  starts a server with 1-8 client DataModels and yields until the server calls `EndTest(result)`;
  `ExecutePlayModeAsync` and `ExecuteRunModeAsync` do the same for solo Test and Run. `AddPlayers`,
  `LeaveTest` and `GetTestArgs` script join and leave flows (`GetTestArgs` has a known issue when
  called from a client LocalScript). Pair it with `UserInputService:CreateVirtualInput()` for
  simulated mouse and keyboard input (it refuses to touch CoreGui) and `StudioDeviceSimulatorService` for scripted device
  profiles. All are Studio-only and do nothing in a published experience.

## Evidence record

For each run record Studio version/date, place/build source, mode, client count, emulated device or
controller, setup, action, expected result, observed result, relevant server/client Output, and
pass/fail. Screenshots help visual review but do not replace interaction or Output evidence.

When the Roblox Studio MCP server is connected, its `get_console_output` and `screen_capture`
tools supply this Output and screenshot evidence directly, and `start_stop_play` plus the
playtest input tools drive the run; the manual testing modes remain the default when it is not.

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
- `https://create.roblox.com/docs/reference/engine/classes/StudioTestService`
