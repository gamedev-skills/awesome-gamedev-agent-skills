#!/usr/bin/env python3
"""Check a tower-defense wave list against its economy: does enemy HP outrun the gold curve?

Reads a JSON spec (waves plus one reference tower) and plays the economy forward: before each
wave the player spends gold on the reference tower, then the tool compares the DPS the wave
demands with the DPS the player owns. The ratio is the wave's pressure:

  pressure = required DPS / (owned DPS x efficiency)
  required = max(total effective HP / time the wave spends in the kill zone,
                 toughest single enemy's effective HP / its own crossing time)

A pressure above 1.0 means the wave leaks even with perfect placement (an ERROR, a "wall").
A run of 3 or more waves below the band's lower edge after the opening waves means the economy
outgrew the HP curve (a WARNING, "trivial"). It is a curve check, not a simulation: it
ignores range overlap, targeting, splash, slows and upgrades (efficiency, default 0.6, stands in
for coverage, overkill and retargeting losses; measure it in a playtest as damage dealt divided
by owned DPS x wave duration), so use it to catch runaway curves, then tune by play.

Exit codes: 0 = no errors (and no warnings with --strict), 1 = errors, or warnings with
--strict, 2 = missing or invalid spec. Standard library only; no network.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

TOOL = "td_curve_check"
SCHEMA = 1
DEFAULT_BAND = (0.6, 0.95)
OPENING_WAVES = 3
TRIVIAL_STREAK = 3

EXAMPLE = """{
  "start_gold": 250,
  "tower": {"cost": 100, "dps": 20},
  "kill_zone": 12,
  "efficiency": 0.6,
  "wave_gen": {"waves": 30, "hp": 40, "hp_growth": 1.12, "count": 8, "count_step": 1,
               "speed": 2.0, "spacing": 0.8, "bounty": 6, "bounty_growth": 1.06,
               "clear_bonus": 30, "clear_bonus_step": 5}
}
Instead of wave_gen, list waves: "waves": [{"groups": [{"hp": 40, "count": 8, "speed": 2,
"spacing": 0.8, "bounty": 6, "armor": 0.0}], "clear_bonus": 30}, ...]. A wave without
"groups" is one group. kill_zone and speed share a unit (tiles and tiles/s)."""


class SpecError(ValueError):
    pass


def number(obj: dict, key: str, default=None, minimum: float = 0.0, below: float | None = None):
    value = obj.get(key, default)
    if value is None:
        raise SpecError(f"missing '{key}'")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SpecError(f"'{key}' must be a number")
    if value < minimum or (below is not None and value >= below):
        bound = f"in [{minimum}, {below})" if below is not None else f">= {minimum}"
        raise SpecError(f"'{key}' must be {bound}, got {value}")
    return float(value)


def build_waves(spec: dict) -> list[dict]:
    if "waves" in spec:
        raw = spec["waves"]
        if not isinstance(raw, list) or not raw:
            raise SpecError("'waves' must be a non-empty list")
        waves = []
        for index, wave in enumerate(raw, 1):
            if not isinstance(wave, dict):
                raise SpecError(f"wave {index} must be an object")
            groups = wave.get("groups", [wave])
            if not isinstance(groups, list) or not groups:
                raise SpecError(f"wave {index}: 'groups' must be a non-empty list")
            parsed = []
            for group in groups:
                if not isinstance(group, dict):
                    raise SpecError(f"wave {index}: each group must be an object")
                try:
                    parsed.append({
                        "hp": number(group, "hp", minimum=1e-9),
                        "count": int(number(group, "count", minimum=1)),
                        "speed": number(group, "speed", minimum=1e-9),
                        "spacing": number(group, "spacing", 0.0),
                        "bounty": number(group, "bounty", 0.0),
                        "armor": number(group, "armor", 0.0, below=1.0),
                    })
                except SpecError as error:
                    raise SpecError(f"wave {index}: {error}") from None
            waves.append({"groups": parsed, "clear_bonus": number(wave, "clear_bonus", 0.0)})
        return waves
    gen = spec.get("wave_gen")
    if not isinstance(gen, dict):
        raise SpecError("spec needs 'waves' or 'wave_gen'")
    total = int(number(gen, "waves", minimum=1))
    waves = []
    for i in range(total):
        waves.append({
            "groups": [{
                "hp": number(gen, "hp", minimum=1e-9) * number(gen, "hp_growth", 1.0) ** i,
                "count": int(number(gen, "count", minimum=1) + number(gen, "count_step", 0.0) * i),
                "speed": number(gen, "speed", minimum=1e-9),
                "spacing": number(gen, "spacing", 0.0),
                "bounty": number(gen, "bounty", 0.0) * number(gen, "bounty_growth", 1.0) ** i,
                "armor": number(gen, "armor", 0.0, below=1.0),
            }],
            "clear_bonus": number(gen, "clear_bonus", 0.0) + number(gen, "clear_bonus_step", 0.0) * i,
        })
    return waves


def required_dps(wave: dict, kill_zone: float) -> tuple[float, float, float]:
    total_ehp, spawn_time, burst = 0.0, 0.0, 0.0
    last_crossing = 0.0
    for group in wave["groups"]:
        ehp = group["hp"] / (1.0 - group["armor"])
        crossing = kill_zone / group["speed"]
        total_ehp += ehp * group["count"]
        spawn_time += group["spacing"] * group["count"]
        burst = max(burst, ehp / crossing)
        last_crossing = crossing
    spawn_time -= wave["groups"][-1]["spacing"]
    window = max(spawn_time, 0.0) + last_crossing
    sustained = total_ehp / window
    return max(sustained, burst), sustained, burst


def analyse(spec: dict, band: tuple[float, float]) -> dict:
    if not isinstance(spec, dict):
        raise SpecError("spec must be a JSON object")
    tower = spec.get("tower")
    if not isinstance(tower, dict):
        raise SpecError("missing 'tower' object with cost and dps")
    cost = number(tower, "cost", minimum=1e-9)
    tower_dps = number(tower, "dps", minimum=1e-9)
    kill_zone = number(spec, "kill_zone", minimum=1e-9)
    gold = number(spec, "start_gold", 0.0)
    efficiency = number(spec, "efficiency", 0.6, minimum=1e-9)
    if efficiency > 1.0:
        raise SpecError("'efficiency' must be at most 1.0")
    waves = build_waves(spec)

    towers, rows, errors, warnings = 0, [], [], []
    streak = 0
    for index, wave in enumerate(waves, 1):
        bought = int(gold // cost)
        towers += bought
        gold -= bought * cost
        owned = towers * tower_dps * efficiency
        need, sustained, burst = required_dps(wave, kill_zone)
        pressure = need / owned if owned else math.inf
        killed = 1.0 if pressure <= 1.0 else 1.0 / pressure
        income = killed * sum(g["bounty"] * g["count"] for g in wave["groups"])
        if pressure <= 1.0:
            income += wave["clear_bonus"]
        if pressure > 1.0:
            verdict = "WALL"
            errors.append(f"wave {index}: pressure {pressure:.2f} > 1.0 (needs {need:.1f} DPS, "
                          f"owns {owned:.1f}); lower HP or raise income before this wave")
        elif pressure < band[0]:
            verdict = "trivial"
        elif pressure > band[1]:
            verdict = "tight"
        else:
            verdict = "ok"
        if verdict == "trivial" and index > OPENING_WAVES:
            streak += 1
            if streak == TRIVIAL_STREAK:
                warnings.append(f"waves {index - TRIVIAL_STREAK + 1}-{index}: pressure below "
                                f"{band[0]} {TRIVIAL_STREAK} waves in a row; HP is not keeping "
                                "up with income")
        else:
            streak = 0
        rows.append({"wave": index, "towers": towers, "owned_dps": owned,
                     "required_dps": need, "sustained_dps": sustained, "burst_dps": burst,
                     "pressure": pressure, "verdict": verdict, "income": income})
        gold += income

    late = [r["pressure"] for r in rows[len(rows) // 2:]] or [rows[-1]["pressure"]]
    early = [r["pressure"] for r in rows[:max(1, len(rows) // 2)]]
    return {"tool": TOOL, "schema": SCHEMA, "band": list(band), "efficiency": efficiency,
            "waves": rows,
            "error_count": len(errors), "warning_count": len(warnings),
            "errors": errors, "warnings": warnings,
            "early_mean_pressure": sum(early) / len(early),
            "late_mean_pressure": sum(late) / len(late)}


def parse_band(text: str) -> tuple[float, float]:
    try:
        low, high = (float(part) for part in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("band must look like 0.6,0.95") from None
    if not 0 < low < high <= 1.0:
        raise argparse.ArgumentTypeError("band needs 0 < low < high <= 1.0")
    return low, high


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="td_curve_check.py", description=__doc__.split("\n\n")[0],
        epilog="Spec example:\n" + EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path, help="JSON spec file")
    parser.add_argument("--band", type=parse_band, default=DEFAULT_BAND,
                        help="target pressure band low,high (0.6,0.95)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if not args.spec.is_file():
        print(f"error: spec not found: {args.spec}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        result = analyse(spec, args.band)
    except (json.JSONDecodeError, SpecError) as error:
        print(f"error: invalid spec: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{'wave':>4} {'towers':>6} {'owned':>8} {'needed':>8} {'pressure':>8}  verdict")
        for row in result["waves"]:
            print(f"{row['wave']:>4} {row['towers']:>6} {row['owned_dps']:>8.1f} "
                  f"{row['required_dps']:>8.1f} {row['pressure']:>8.2f}  {row['verdict']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        print(f"Summary: {result['error_count']} error(s), {result['warning_count']} warning(s); "
              f"mean pressure early {result['early_mean_pressure']:.2f}, "
              f"late {result['late_mean_pressure']:.2f}")
    if result["errors"] or (args.strict and result["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
