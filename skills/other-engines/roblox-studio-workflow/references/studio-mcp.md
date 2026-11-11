# Roblox Studio MCP server: tool map

Read this when Studio MCP tools are available in the session (for example `list_roblox_studios`
or `execute_luau`), or when you plan a workflow around them. Tool names change with Studio
releases; this list was checked on 2026-11-11. When it disagrees with the tools your client lists,
trust the client.

## Connection facts

- The server is built into Studio and speaks MCP over stdio. The user turns it on in Assistant
  (… → Manage MCP Servers, or Settings → MCP Servers in newer builds) with *Enable Studio as MCP
  server*. Quick connect covers Claude Code, Claude Desktop, Codex CLI, Cursor, Gemini CLI, VS Code
  and Antigravity.
- Roblox's official agent plugin (`Roblox/roblox-studio-agent-plugin`) ships the
  `roblox-get-started` skill, which installs and connects Studio. Hand setup, sign-in, and "tools
  missing" problems to it when it is installed; otherwise give the user the manual steps above.
- Every call takes a `studio_id`. Call `list_roblox_studios` first and pick the place by name and
  place ID; an empty list means Studio is closed, no place is open, or the setting is off.
- Connected clients can read and change every open place. Ask the user to save or publish a
  version before large edits; not every change can be undone from Studio.

## Ladder step to tool

| Ladder step | Tools |
|---|---|
| inventory | `search_game_tree`, `inspect_instance`, `script_search`, `script_grep`, `script_read` |
| edit | `multi_edit` (creates the script when the path is new), `execute_luau` on `Edit` for Instance changes |
| run | `get_studio_state`, `start_stop_play`, `execute_luau` (`datamodel_type` `Edit`, `Client` or `Server`) |
| evidence | `get_console_output`, `screen_capture` |
| playtest input | `character_navigation`, `user_keyboard_input`, `user_mouse_input`, `subagent` (types `explore`, `playtest`) |
| assets | `search_asset`, `insert_asset`, `generate_*` tools plus `wait_job_finished` |
| docs and know-how | `http_get` (Roblox docs only), `skill` (Studio's built-in skills) |
| save | `save_place` (same as File → Save, no dialogs) |

The plugin's README lists more tools than the docs page (for example `list_skills`,
`open_cloud_invoke`, `create_skill`). Use what the client exposes.

## Studio's built-in skills worth calling

Reach these through the `skill` tool. They update with Studio, so prefer them for live-editor
work and keep this repo's skills for what to build and what to cover.

| Built-in skill | Use it for |
|---|---|
| `rbx-debug` | breakpoints, call stacks and locals instead of print debugging |
| `rbx-unit-test` | running ModuleScript tests (detects Jest-Lua or TestEZ, has a fallback harness) |
| `rbx-device-simulator-lua` | switching device presets and capturing UI per form factor |
| `rbx-perf-profiling`, `rbx-scene-analysis` | real MicroProfiler and scene-cost data |
| `rbx-docs-search` | current Engine API pages |
| `rbx-configs-experimentation`, `rbx-instrument-analytics` | live configs, A/B tests, analytics events |

## Limits to plan around

- `start_stop_play` starts one solo client. Multi-client checks need Server & Clients (the user)
  or a `StudioTestService` plugin harness.
- `multi_edit` and `execute_luau` change the place directly. Keep the same discipline as manual
  work: edit the source of truth (a Rojo-synced script edited in Studio is overwritten by the next
  sync), keep authored Instances inspectable, and clean up experiments.
- An inserted Creator Store model can carry its own Scripts. Inspect its descendants before
  keeping it, as you would any third-party code.
- Studio Assistant skills are single Markdown files; this repo's skills with `references/` work in
  external agents connected to Studio but cannot be pasted into Assistant as they are.

## Sources

- `https://create.roblox.com/docs/studio/mcp`
- `https://create.roblox.com/docs/assistant/skills`
- `https://github.com/Roblox/roblox-studio-agent-plugin`
