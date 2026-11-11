#!/usr/bin/env python3
"""Derive platformer jump physics from feel targets and check them at a fixed tick.

Give the jump you want (height in tiles, seconds to apex) and the tick rate the controller
runs at. The tool prints gravity, launch speed and fall gravity, then simulates the jump at
that tick the way most engines integrate (velocity += g*dt, then position += velocity*dt) and
reports the apex it really reaches, airtime, the tap-jump height, gap reach, grace windows in
ticks and tunnelling risk.

With --log it also compares a jump recorded from the game (CSV with t and y columns, one row
per physics tick, starting on the tick the jump fired) against the targets and exits 1 when
the measured apex height or time to apex is outside the tolerance.

Exit codes: 0 = no errors (and no warnings with --strict), 1 = log mismatch, or warnings with
--strict, 2 = invalid arguments or unreadable log. Standard library only; no network.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

TOOL = "jump_tuner"
SCHEMA = 1

# Ranges are starting points from shipped games (Celeste's Player.cs: 0.1 s coyote time,
# ~0.37 s to apex, short hop ~20% of a full jump) and common tuning practice, not rules.
APEX_TIME_RANGE = (0.25, 0.50)
FALL_MULT_RANGE = (1.0, 3.0)
COYOTE_RANGE = (0.05, 0.15)
BUFFER_RANGE = (0.05, 0.20)
HOP_RATIO_RANGE = (0.15, 0.60)
APEX_ERROR_LIMIT = 0.03


def positive(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive number, got {text}")
    return value


def non_negative(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError(f"must be zero or positive, got {text}")
    return value


def unit_interval(text: str) -> float:
    value = float(text)
    if not 0 <= value <= 1:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {text}")
    return value


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jump_tuner.py",
        description=__doc__.split("\n\n")[0],
        epilog="Example: jump_tuner.py --height 3.5 --apex-time 0.35 --tile 16 --tick 60 "
               "--run-speed 8 --log jump_log.csv",
    )
    parser.add_argument("--height", type=positive, default=3.5, help="jump height in tiles (3.5)")
    parser.add_argument("--apex-time", type=positive, default=0.35, help="seconds to apex (0.35)")
    parser.add_argument("--tile", type=positive, default=16.0, help="world units per tile (16)")
    parser.add_argument("--fall-mult", type=positive, default=1.8,
                        help="fall gravity / rise gravity (1.8)")
    parser.add_argument("--max-fall", type=positive, default=None,
                        help="terminal fall speed in tiles/s (default: no cap)")
    parser.add_argument("--tick", type=positive, default=60.0, help="physics ticks per second (60)")
    parser.add_argument("--coyote", type=non_negative, default=0.1, help="coyote time, s (0.1)")
    parser.add_argument("--buffer", type=non_negative, default=0.12, help="jump buffer, s (0.12)")
    parser.add_argument("--cut", type=unit_interval, default=0.5,
                        help="upward velocity multiplier on early release (0.5)")
    parser.add_argument("--run-speed", type=positive, default=None,
                        help="top run speed in tiles/s, to report gap reach")
    parser.add_argument("--integrator", choices=("euler", "half"), default="euler",
                        help="euler: v+=g*dt then move (most engines); half: half-step gravity")
    parser.add_argument("--log", type=Path, default=None,
                        help="CSV of a recorded jump with t and y columns, one row per tick")
    parser.add_argument("--y-up", action="store_true", help="log y grows upward (default: down)")
    parser.add_argument("--tolerance", type=unit_interval, default=0.05,
                        help="allowed relative error for --log checks (0.05)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    return parser.parse_args(argv)


def simulate(launch: float, rise_g: float, fall_g: float, dt: float, max_fall: float | None,
             integrator: str, cut_after_first_tick: float | None = None) -> dict:
    """Simulate one jump on flat ground. y grows upward here; returns apex and timings."""
    y, vy, t = 0.0, launch, 0.0
    apex, apex_t, ticks = 0.0, 0.0, 0
    while True:
        ticks += 1
        g = rise_g if vy > 0 else fall_g
        if integrator == "half":
            vy -= 0.5 * g * dt
            y += vy * dt
            vy -= 0.5 * g * dt
        else:
            vy -= g * dt
            y += vy * dt
        if max_fall is not None:
            vy = max(vy, -max_fall)
        if ticks == 1 and cut_after_first_tick is not None and vy > 0:
            vy *= cut_after_first_tick
        t = ticks * dt
        if y > apex:
            apex, apex_t = y, t
        if y <= 0.0:
            return {"apex": apex, "apex_time": apex_t, "airtime": t, "landing_speed": -vy}
        if ticks > 100_000:
            raise RuntimeError("jump never landed; check gravity")


def grace_ticks(seconds: float, dt: float) -> int:
    """Ticks a timer stays open with the usual 'timer -= dt; if timer > 0' countdown."""
    timer, ticks = seconds, 0
    while True:
        timer -= dt
        if timer > 0:
            ticks += 1
        else:
            return ticks


def read_log(path: Path, y_up: bool) -> list[tuple[float, float]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = {name.strip().lower(): name for name in (reader.fieldnames or [])}
            t_key = fields.get("t") or fields.get("time")
            y_key = fields.get("y")
            if not t_key or not y_key:
                raise ValueError("log needs a header with t (or time) and y columns")
            rows = [(float(row[t_key]), float(row[y_key])) for row in reader if row.get(y_key)]
    except OSError as error:
        raise ValueError(f"cannot read log: {error}") from error
    if len(rows) < 3:
        raise ValueError("log needs at least 3 samples")
    t0, y0 = rows[0]
    sign = 1.0 if y_up else -1.0
    return [(t - t0, sign * (y - y0)) for t, y in rows]


def check_log(samples: list[tuple[float, float]], target_height: float, target_apex: float,
              tolerance: float, dt: float) -> dict:
    apex_index = max(range(len(samples)), key=lambda i: samples[i][1])
    apex_t, apex_h = samples[apex_index]
    landed = next((t for t, h in samples[apex_index + 1:] if h <= 0.0), None)
    height_error = (apex_h - target_height) / target_height
    time_error = apex_t - target_apex
    time_limit = max(tolerance * target_apex, dt)
    problems = []
    if abs(height_error) > tolerance:
        problems.append(f"apex height {apex_h:.2f} vs target {target_height:.2f} "
                        f"({height_error:+.1%})")
    if abs(time_error) > time_limit:
        problems.append(f"time to apex {apex_t:.3f}s vs target {target_apex:.3f}s "
                        f"({time_error:+.3f}s)")
    return {"apex_height": apex_h, "apex_time": apex_t, "airtime": landed,
            "height_error": height_error, "apex_time_error": time_error,
            "ok": not problems, "problems": problems}


def analyse(args: argparse.Namespace) -> dict:
    dt = 1.0 / args.tick
    height = args.height * args.tile
    rise_g = 2.0 * height / args.apex_time ** 2
    launch = 2.0 * height / args.apex_time
    fall_g = rise_g * args.fall_mult
    max_fall = args.max_fall * args.tile if args.max_fall else None

    full = simulate(launch, rise_g, fall_g, dt, max_fall, args.integrator)
    hop = simulate(launch, rise_g, fall_g, dt, max_fall, args.integrator, args.cut)
    apex_error = (full["apex"] - height) / height
    hop_ratio = hop["apex"] / full["apex"]
    terminal = max_fall if max_fall else full["landing_speed"]
    per_tick_fall = terminal * dt

    result = {
        "tool": TOOL, "schema": SCHEMA,
        "inputs": {"height_tiles": args.height, "apex_time": args.apex_time, "tile": args.tile,
                   "fall_mult": args.fall_mult, "max_fall_tiles_s": args.max_fall,
                   "tick": args.tick, "coyote": args.coyote, "buffer": args.buffer,
                   "cut": args.cut, "run_speed_tiles_s": args.run_speed,
                   "integrator": args.integrator},
        "derived": {"rise_gravity": rise_g, "fall_gravity": fall_g, "jump_speed": launch,
                    "jump_velocity_y_down": -launch},
        "simulated": {
            "apex": full["apex"], "apex_tiles": full["apex"] / args.tile,
            "apex_error": apex_error, "apex_time": full["apex_time"],
            "airtime": full["airtime"], "landing_speed": full["landing_speed"],
            "tap_hop": hop["apex"], "tap_hop_tiles": hop["apex"] / args.tile,
            "tap_hop_ratio": hop_ratio,
            "coyote_ticks": grace_ticks(args.coyote, dt),
            "coyote_ticks_rounded": round(args.coyote * args.tick),
            "buffer_ticks": grace_ticks(args.buffer, dt),
            "buffer_ticks_rounded": round(args.buffer * args.tick),
            "fall_per_tick": per_tick_fall,
            "gap_reach_tiles": (args.run_speed * full["airtime"]) if args.run_speed else None,
        },
        "warnings": [], "log_check": None,
    }
    warn = result["warnings"].append
    sim = result["simulated"]
    if not APEX_TIME_RANGE[0] <= args.apex_time <= APEX_TIME_RANGE[1]:
        warn(f"apex time {args.apex_time}s is outside {APEX_TIME_RANGE}: "
             "below feels twitchy, above feels floaty")
    if not FALL_MULT_RANGE[0] <= args.fall_mult <= FALL_MULT_RANGE[1]:
        warn(f"fall multiplier {args.fall_mult} is outside {FALL_MULT_RANGE}")
    if abs(apex_error) > APEX_ERROR_LIMIT:
        warn(f"the {args.tick:g} Hz step reaches {sim['apex_tiles']:.2f} tiles, "
             f"{apex_error:+.1%} off the design; use --integrator half or retune")
    if not HOP_RATIO_RANGE[0] <= hop_ratio <= HOP_RATIO_RANGE[1]:
        warn(f"tap hop is {hop_ratio:.0%} of a full jump; aim for 15-60% "
             "(change --cut)")
    if not COYOTE_RANGE[0] <= args.coyote <= COYOTE_RANGE[1]:
        warn(f"coyote time {args.coyote}s is outside {COYOTE_RANGE}")
    if not BUFFER_RANGE[0] <= args.buffer <= BUFFER_RANGE[1]:
        warn(f"jump buffer {args.buffer}s is outside {BUFFER_RANGE}")
    for name in ("coyote", "buffer"):
        counted, rounded = sim[f"{name}_ticks"], sim[f"{name}_ticks_rounded"]
        if counted != rounded:
            warn(f"{name} {getattr(args, name)}s gives {counted} ticks with a float countdown "
                 f"but {rounded} by rounding; count grace windows in whole ticks")
    if per_tick_fall > args.tile / 2:
        warn(f"falling moves {per_tick_fall:.1f} units per tick, over half a tile; "
             "cap fall speed or use continuous collision")
    if args.log is not None:
        samples = read_log(args.log, args.y_up)
        result["log_check"] = check_log(samples, height, args.apex_time, args.tolerance, dt)
    return result


def print_text(result: dict) -> None:
    d, s, i = result["derived"], result["simulated"], result["inputs"]
    print(f"Target: {i['height_tiles']:g} tiles ({i['height_tiles'] * i['tile']:g} units) "
          f"in {i['apex_time']:g}s, {i['tick']:g} Hz, {i['integrator']} integration")
    print(f"  rise gravity   {d['rise_gravity']:.2f} units/s^2")
    print(f"  fall gravity   {d['fall_gravity']:.2f} units/s^2 (x{i['fall_mult']:g})")
    print(f"  jump velocity  {d['jump_velocity_y_down']:.2f} units/s (y down; "
          f"+{d['jump_speed']:.2f} if y is up)")
    print(f"Simulated: apex {s['apex_tiles']:.3f} tiles ({s['apex_error']:+.2%}) at "
          f"{s['apex_time']:.3f}s, airtime {s['airtime']:.3f}s, lands at "
          f"{s['landing_speed']:.1f} units/s")
    print(f"  tap hop {s['tap_hop_tiles']:.2f} tiles ({s['tap_hop_ratio']:.0%} of full)")
    print(f"  coyote {s['coyote_ticks']} ticks, buffer {s['buffer_ticks']} ticks")
    if s["gap_reach_tiles"] is not None:
        print(f"  gap reach at top speed ~{s['gap_reach_tiles']:.1f} tiles "
              "(minus collider width)")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    log = result["log_check"]
    if log:
        state = "OK" if log["ok"] else "MISMATCH"
        print(f"Log: apex {log['apex_height']:.2f} units at {log['apex_time']:.3f}s -> {state}")
        for problem in log["problems"]:
            print(f"ERROR: {problem}")
    errors = len(log["problems"]) if log else 0
    print(f"Summary: {errors} error(s), {len(result['warnings'])} warning(s)")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = analyse(args)
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_text(result)
    log = result["log_check"]
    if log and not log["ok"]:
        return 1
    if args.strict and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
