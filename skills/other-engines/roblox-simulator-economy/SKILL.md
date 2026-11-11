---
name: roblox-simulator-economy
description: >
  Roblox simulator, tycoon and idle-game economies in Luau: upgrade cost curves, income per
  second, rebirth pacing, big-number formatting and paid-egg odds, with a Lune calculator. Use for
  baseCost or rebirth numbers or unearned currency. Not for DataStores (`roblox-datastores`),
  remote limits (`roblox-networking`), shop layout (`roblox-ui`) or wave economies
  (`tower-defense`).
---

# Roblox simulator economy

Choose the economy's numbers with a pacing table before writing gameplay code, then implement them
so the server owns every amount. The bundled scripts are pure Luau and run outside Studio with
Lune (install it from `https://github.com/lune-org/lune/releases`; `lune --version` to check).

## Workflow

1. **Inspect.** Find where currency, upgrade, and rebirth values live now and which scripts change
   them. List every RemoteEvent that touches currency and what each one sends.
2. **Write the numbers as one config table**: base income; each upgrade's `baseCost`,
   `costGrowth`, effect, and `maxLevel`; rebirth `baseRequirement`, `requirementGrowth`,
   `multiplierPerRebirth`; offline `maxHours`, `efficiency`. Server and client both read it.
3. **Run the pacing calculator** from the skill directory (paths are relative to it):
   `lune run scripts/balance.luau --print-defaults > economy.json`, edit the file, then
   `lune run scripts/balance.luau economy.json`. Read the `wait` and `vs prev` columns and tune
   until they match the targets below. `--help` lists every field and its allowed range; a
   missing file, invalid JSON, or out-of-range field prints an error and exits 1.
4. **Implement on the server** with the patterns below; read
   [references/server-patterns.md](references/server-patterns.md) for the full handlers. Copy
   `scripts/economy_math.luau` unchanged into a ModuleScript so the maths you tested is the maths
   that runs.
5. **Verify.** Run `lune run scripts/test_economy_math.luau` (exits 1 on failure) after any change
   to the maths module, and re-run the calculator on the final config. In Studio, with the MCP
   server connected, start play and fire the purchase handlers from `execute_luau` on the `Server`
   datamodel with valid ids, unknown ids, `0/0`, `math.huge` and negative values, then read
   `get_console_output` and the wallet. Purchases from two players, rebirth, and leave-and-rejoin
   need Server & Clients: ask the user to run them and report balances before and after.

## Formulas

| Quantity | Formula | Notes |
|---|---|---|
| Price of the next level | `floor(baseCost * costGrowth ^ owned)` | 1.07-1.15 for upgrades bought many times; 1.5-3 for rare large ones |
| Cost from level a to b | `baseCost * g^a * (g^(b-a) - 1) / (g - 1)` | Players pay the floored per-level sum, slightly less |
| Buy max | walk real prices until the next exceeds the balance or `maxLevel` | Safer than the log formula with floored prices |
| Rebirth requirement k | `baseRequirement * requirementGrowth ^ k` | |
| Rebirth multiplier | `1 + k * multiplierPerRebirth` | Additive grows slowly; multiplicative (`q ^ k`) grows exponentially |
| Offline income | `floor(min(away, maxHours * 3600) * rate * efficiency)` | Away time of 0 or less (clock went back) pays 0 |

Read [references/formulas.md](references/formulas.md) when you need a derivation, want to solve
for a parameter instead of trying values, or must explain the calculator's output.

## Pacing targets (starting points, not rules)

- **Early upgrades take seconds.** In the default config the first 10 levels take 3-10 s each.
- **Each rebirth should take only a little longer than the last**, for example x1.2-x1.5. The
  calculator's `vs prev` column is that ratio. With an additive multiplier it approaches
  `requirementGrowth` over time, so `requirementGrowth = 3` gives x2.0 rising to x2.7 and rebirth 8
  takes 137 days at the default income. `requirementGrowth = 1.8` gives x1.2 rising to x1.6.
- **Offline earns less than online.** An efficiency of 0.25-0.5 and an 8-12 hour cap keep playing
  worth more than idling without zeroing out players who log off.

## Server-owned purchases

A RemoteEvent carries what the player wants ("buy upgrade `Income`"), never an amount or a price.
The server looks up the price, checks the balance, spends, and grants without yielding in between.

```lua
-- ServerScriptService/Economy.server.luau (excerpt; full version in references/server-patterns.md)
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local EconomyMath = require(ReplicatedStorage.Shared.EconomyMath)
local Config = require(ReplicatedStorage.Shared.EconomyConfig)

ReplicatedStorage.Remotes.BuyUpgrade.OnServerEvent:Connect(function(player: Player, upgradeId: unknown)
	local session = sessions[player]
	if not session or type(upgradeId) ~= "string" then return end
	local upgrade = Config.upgrades[upgradeId]
	if not upgrade then return end -- unknown id
	local owned = session.levels[upgradeId] or 0
	if owned >= upgrade.maxLevel then return end
	local price = EconomyMath.levelCost(upgrade.baseCost, upgrade.costGrowth, owned)
	if EconomyMath.trySpend(session.wallet, { [upgrade.currency] = price }) then
		session.levels[upgradeId] = owned + 1
	end
end)
```

- `trySpend` checks every currency in a multi-currency cost before subtracting any, and rejects
  negative or non-finite costs.
- **Rebirth on the server**: compare the server's balance with the requirement, then reset wallet
  and levels and increment the count. Never accept "I rebirthed" or a balance from the client.
- Rate-limit each remote per player with a token bucket (`roblox-networking`).

## Save data and offline time

- **Repair on load; never error.** Use `sanitizeAmount` (non-numbers, NaN, infinity and negatives
  become 0; fractions are floored) and `sanitizeLevel` (also clamps to the current `maxLevel`).
  Drop unknown upgrade ids and return a list of what was repaired, so old versions and edited data
  load cleanly.
- **Never save NaN or infinity.** A division by zero that reaches the wallet should be caught by
  the same sanitizers before saving.
- **Offline time comes from the server clock only**: save `os.time()` on the server when the
  player leaves; on join, `away = os.time() - lastSeen`. A missing or future `lastSeen` counts as
  now, which pays nothing.
- **Precision:** Luau numbers are doubles, exact for integers up to `2^53` (about `9e15`). If
  balances can pass about `1e15`, store a mantissa/exponent pair or a base-10 logarithm instead.

## Big-number display

`EconomyMath.formatNumber(value, decimals?)` uses the suffixes K, M, B, T, Qa, Qi, Sx, Sp, Oc, No,
Dc, Ud, Dd, Td, Qad, Qid, Sxd, Spd, Ocd, Nod, Vg (`1e63`), then scientific notation.

- **The rollover bug:** `999950 / 1000 = 999.95`, which rounds to `"1000.0K"`. Round first; if the
  rounded value reaches 1000, move to the next suffix (`"1.0M"`). The tests cover this case.
- Format on the client for display only; never parse a formatted string back into a number.

## Paid random items (eggs, crates, spins)

Roblox's paid random items policy applies when a random item is bought with Robux, directly or
through in-game currency bought with Robux. The current rules are summarized under Version notes;
re-read the policy page before shipping. The implementation rule does not change: build the odds
panel and the roll from one list.

Build the odds panel with `EconomyMath.oddsPercent(outcomes)` and roll on the server with
`EconomyMath.pickWeighted(outcomes, rng:NextNumber())` from the **same** list (after applying any
boost), so shown and actual odds cannot drift. Check `PolicyService:GetPolicyInfoForPlayerAsync()` before
the spend and apply a restricted-player treatment when `ArePaidRandomItemsRestricted` is true.

For live tuning of prices and rewards without a server restart, and for funnel and currency
analytics, Studio's built-in `rbx-configs-experimentation` and `rbx-instrument-analytics` skills
(through the Studio MCP `skill` tool) cover ConfigService and AnalyticsService; this skill supplies
the numbers.

## Gotchas

- **Rebirth 6 takes weeks** → `requirementGrowth` far above the multiplier's growth; read the
  `vs prev` column and lower `requirementGrowth` or switch to a multiplicative multiplier.
- **Prices outrun income after ~20 levels** → `costGrowth` of 1.5+ on an upgrade meant
  to be bought 50 times (level 50 costs about 637 million times level 0); use 1.07-1.15.
- **Late game breaks after a few rebirths** → multiplicative multiplier (`1.5 ^ k`) without a
  matching requirement curve; keep `requirementGrowth / q` near the ratio you want.
- **Players gain currency they did not earn** → a remote accepts an amount or price, or the check
  happens only on the client; send ids, price on the server.
- **Two purchases pass one balance check** → the handler yields between check and spend; spend
  before any `task.wait`, DataStore call, or other yield.
- **Buy max freezes the server** → uncapped loop or a price of 0; pass `maxLevel`, keep
  `baseCost >= 1` (`maxAffordable` errors instead of looping forever).
- **Offline pays days of income** → client timestamp, no cap, or a corrupted `lastSeen`; use the
  server clock, cap, and treat future times as now.
- **HUD shows "1000.0K"** → `math.floor(x * 10) / 10` before choosing the suffix; use
  `formatNumber`.
- **A save fails or loads as garbage** → NaN or infinity reached the wallet; sanitize before save
  and on load.
- **Odds panel wrong after a one-per-player pet is owned** → outcomes a player can no longer get
  must leave the shown and rolled list; rebuild both from the same filtered list.

## Resources

Script paths are relative to the skill directory.

- `scripts/balance.luau`: run it (`--help` first) whenever you choose or change economy numbers.
  Prints per-level price, total, income and wait; per-rebirth requirement, multiplier, wait and
  ratio; offline maximum.
- `scripts/economy_math.luau`: copy it unchanged into a ModuleScript; read it only to look up a
  function's arguments. Formulas, `trySpend`, sanitizers, odds and `formatNumber`.
- `scripts/test_economy_math.luau`: run it after any change to the maths module (exits 1 on
  failure).
- [references/formulas.md](references/formulas.md): read when you need a derivation or the
  rebirth wait-ratio formula.
- [references/server-patterns.md](references/server-patterns.md): read when you implement the
  handlers: config layout, income tick, buy max, rebirth, load repair with offline income, and
  paid random item rolls.

## Related skills

- `roblox-luau` — services, ModuleScripts, and the client/server split.
- `roblox-networking` — remote validation and token-bucket rate limits.
- `roblox-datastores` — loading and saving the session this skill repairs.
- `roblox-ui` — shop, upgrade, and odds panels.
- `roblox-studio-workflow` — Server & Clients playtests.

## Version notes

Last verified: 2026-11-11.

- Scripts and tests pass under Lune 0.11.1 (13 tests); the worked example in
  `references/formulas.md` was produced with 0.11.0 and matches 0.11.1 output.
- Paid random items policy, as summarized from the Creator Hub page:
  - Show every outcome and its actual odds as percentages summing to exactly 100% before purchase.
    Long decimals may be rounded with a note that the shown total may not equal 100%.
  - If the list does not fit, open it from a control labelled "Info" or "Details" that is visible
    before purchase; an "(i)" icon alone is not enough.
  - Luck boosts, pity systems and other probability modifiers count: explain their effect
    numerically before purchase and show the boosted odds while active.
  - When a player can get an outcome only once, update the remaining odds for that player.
  - `ArePaidRandomItemsRestricted`: give those players a listed treatment (free earnable path,
    fixed disclosed order, direct purchase at expected value, hide, block with a message, or move
    them away). `IsPaidItemTradingAllowed`: when false, those players must not trade paid outcomes.

Sources: `https://create.roblox.com/docs/production/monetization/paid-random-items`,
`https://create.roblox.com/docs/reference/engine/classes/PolicyService`,
`https://create.roblox.com/docs/reference/engine/datatypes/Random`,
`https://create.roblox.com/docs/assistant/skills`,
`https://github.com/lune-org/lune/releases` (0.11.1, 2026-10-21).
