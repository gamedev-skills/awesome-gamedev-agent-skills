# Server patterns for a Roblox simulator economy

Read this when you implement the economy in a place: the shared config, the income tick, buy max,
rebirth, offline earnings on join, repairing loaded data, and rolling paid random items. Persistence
calls (`GetAsync`/`UpdateAsync`, session locking, retries) belong to `roblox-datastores`; remote
rate limits and payload validation in depth belong to `roblox-networking`.

Contents:
- Layout
- Sessions and the income tick
- Buy one and buy max
- Rebirth
- Loading: repair first, then pay offline income
- Paid random items (eggs, crates, spins)

The snippets use only `Players`, `ReplicatedStorage`, `PolicyService`, `RemoteEvent`, `Random`,
`task`, and `os.time()`. They were compiled and run under Lune 0.11.0 against minimal stand-ins
for those services (not shipped with this skill); behaviour inside Studio still needs a Server &
Clients playtest.

## Layout

```text
ReplicatedStorage/
  Shared/EconomyMath      ModuleScript: scripts/economy_math.luau, unchanged
  Shared/EconomyConfig    ModuleScript: the numbers (same shape as balance.luau's JSON)
  Remotes/BuyUpgrade      RemoteEvent  (client -> server: upgrade id)
  Remotes/BuyMax          RemoteEvent  (client -> server: upgrade id)
  Remotes/Rebirth         RemoteEvent  (client -> server: no arguments)
  Remotes/WalletChanged   RemoteEvent  (server -> client: wallet snapshot)
ServerScriptService/
  Economy.server.luau     owns every session table
```

The config sits in `ReplicatedStorage` so the client can show prices and odds from the same table
the server uses. That is safe because the server never reads amounts from the client.

```lua
-- ReplicatedStorage/Shared/EconomyConfig
return {
	baseIncome = 1,
	upgrades = {
		Income = { currency = "Coins", baseCost = 10, costGrowth = 1.15, incomePerLevel = 1, maxLevel = 100 },
	},
	rebirth = { baseRequirement = 1e6, requirementGrowth = 1.8, multiplierPerRebirth = 0.5 },
	offline = { maxHours = 8, efficiency = 0.5 },
	eggs = {
		Basic = {
			price = { Coins = 500 },
			outcomes = {
				{ id = "Cat", weight = 70 },
				{ id = "Dog", weight = 25 },
				{ id = "Dragon", weight = 5 },
			},
		},
	},
}
```

## Sessions and the income tick

```lua
-- ServerScriptService/Economy.server.luau
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local EconomyMath = require(ReplicatedStorage.Shared.EconomyMath)
local Config = require(ReplicatedStorage.Shared.EconomyConfig)
local Remotes = ReplicatedStorage.Remotes

type Session = {
	wallet: { [string]: number },
	levels: { [string]: number },
	rebirths: number,
	carry: number, -- fractional income not yet paid
}
local sessions: { [Player]: Session } = {}

local function incomePerSecond(session: Session): number
	local upgrade = Config.upgrades.Income
	local base = Config.baseIncome + (session.levels.Income or 0) * upgrade.incomePerLevel
	return base * EconomyMath.rebirthMultiplier(Config.rebirth.multiplierPerRebirth, session.rebirths)
end

local function pushWallet(player: Player, session: Session)
	Remotes.WalletChanged:FireClient(player, table.clone(session.wallet))
end

task.spawn(function()
	while true do
		local elapsed = task.wait(1)
		for player, session in sessions do
			session.carry += incomePerSecond(session) * elapsed
			local whole = math.floor(session.carry)
			session.carry -= whole
			session.wallet.Coins = (session.wallet.Coins or 0) + whole
			pushWallet(player, session)
		end
	end
end)
```

`task.wait` returns the time that actually passed, so a slow frame does not lose income, and the
`carry` field keeps fractional multipliers (x1.5 on 41/s) from being floored away every second.

## Buy one and buy max

```lua
Remotes.BuyUpgrade.OnServerEvent:Connect(function(player: Player, upgradeId: unknown)
	local session = sessions[player]
	if not session or type(upgradeId) ~= "string" then return end
	local upgrade = Config.upgrades[upgradeId]
	if not upgrade then return end
	local owned = session.levels[upgradeId] or 0
	if owned >= upgrade.maxLevel then return end
	local price = EconomyMath.levelCost(upgrade.baseCost, upgrade.costGrowth, owned)
	if EconomyMath.trySpend(session.wallet, { [upgrade.currency] = price }) then
		session.levels[upgradeId] = owned + 1
		pushWallet(player, session)
	end
end)

Remotes.BuyMax.OnServerEvent:Connect(function(player: Player, upgradeId: unknown)
	local session = sessions[player]
	if not session or type(upgradeId) ~= "string" then return end
	local upgrade = Config.upgrades[upgradeId]
	if not upgrade then return end
	local owned = session.levels[upgradeId] or 0
	local money = session.wallet[upgrade.currency] or 0
	local count, total = EconomyMath.maxAffordable(upgrade.baseCost, upgrade.costGrowth, owned, money, upgrade.maxLevel)
	if count > 0 and EconomyMath.trySpend(session.wallet, { [upgrade.currency] = total }) then
		session.levels[upgradeId] = owned + count
		pushWallet(player, session)
	end
end)
```

Neither handler yields between the balance check and the spend, so two requests from the same
player cannot both pass the check. Put a per-player token bucket (see `roblox-networking`) in front
of both before shipping.

## Rebirth

```lua
Remotes.Rebirth.OnServerEvent:Connect(function(player: Player)
	local session = sessions[player]
	if not session then return end
	local rb = Config.rebirth
	local requirement = EconomyMath.rebirthRequirement(rb.baseRequirement, rb.requirementGrowth, session.rebirths)
	if (session.wallet.Coins or 0) < requirement then return end
	session.wallet.Coins = 0
	table.clear(session.levels)
	session.carry = 0
	session.rebirths += 1
	pushWallet(player, session)
end)
```

## Loading: repair first, then pay offline income

`saved` is whatever `roblox-datastores` loaded (or `nil` for a new player). Repairing never errors
and reports what it changed, so you can log tampering or old-version data.

```lua
local function repair(saved: any, now: number): (Session, { string })
	local notes = {}
	local data = if type(saved) == "table" then saved else {}
	local session: Session = { wallet = {}, levels = {}, rebirths = 0, carry = 0 }

	local wallet = if type(data.wallet) == "table" then data.wallet else {}
	for currency, amount in wallet do
		local fixed = EconomyMath.sanitizeAmount(amount)
		if fixed ~= amount then table.insert(notes, `wallet.{currency}`) end
		if type(currency) == "string" then session.wallet[currency] = fixed end
	end

	local levels = if type(data.levels) == "table" then data.levels else {}
	for id, level in levels do
		local upgrade = Config.upgrades[id]
		if upgrade then
			local fixed = EconomyMath.sanitizeLevel(level, upgrade.maxLevel)
			if fixed ~= level then table.insert(notes, `levels.{id}`) end
			session.levels[id] = fixed
		else
			table.insert(notes, `dropped unknown upgrade {tostring(id)}`)
		end
	end

	session.rebirths = EconomyMath.sanitizeAmount(data.rebirths)

	-- Offline income from the server clock only. A missing, non-number or future
	-- timestamp counts as "now", which pays nothing.
	local lastSeen = data.lastSeen
	if type(lastSeen) ~= "number" or not (lastSeen <= now) then
		lastSeen = now
	end
	local off = Config.offline
	local paid = EconomyMath.offlineIncome(now - lastSeen, incomePerSecond(session), off.maxHours, off.efficiency)
	session.wallet.Coins = (session.wallet.Coins or 0) + paid
	return session, notes
end
```

On leave, save `lastSeen = os.time()` from the server along with the wallet, levels and rebirth
count, then clear `sessions[player]` in `Players.PlayerRemoving`. Never accept a timestamp from the
client.

## Paid random items (eggs, crates, spins)

The rules come from Roblox's
[paid random items guidelines](https://create.roblox.com/docs/production/monetization/paid-random-items);
this section only shows how to keep the shown odds and the roll identical.

```lua
local PolicyService = game:GetService("PolicyService")
local rng = Random.new()

local function paidRandomItemsRestricted(player: Player): boolean
	local ok, policy = pcall(PolicyService.GetPolicyInfoForPlayerAsync, PolicyService, player)
	-- If the policy lookup fails, treat the player as restricted.
	return not ok or policy.ArePaidRandomItemsRestricted
end

local function openEgg(player: Player, eggId: string): string?
	local session = sessions[player]
	local egg = Config.eggs[eggId]
	if not session or not egg then return nil end
	-- Only needed when the price currency can be bought with Robux.
	if paidRandomItemsRestricted(player) then return nil end
	if sessions[player] ~= session then return nil end -- player left during the lookup
	if not EconomyMath.trySpend(session.wallet, egg.price) then return nil end
	local outcomes = egg.outcomes -- apply luck boosts here and show this same list
	return EconomyMath.pickWeighted(outcomes, rng:NextNumber())
end
```

The client builds the odds panel from `EconomyMath.oddsPercent(Config.eggs[eggId].outcomes)` (or
the boosted list the server sends while a boost is active), so the panel shows exactly what the
server rolls. `GetPolicyInfoForPlayerAsync` yields, so it runs before the spend, and the session
is checked again afterwards. For restricted players, the guidelines list the allowed treatments
(for example a free earnable path, a fixed non-random order shown before purchase, or hiding or
blocking the item); pick one deliberately.
