#!/usr/bin/env python3
"""Check and run the skill trigger evals in evals/triggers.json.

--check validates the eval file offline. --judge-cmd sends one selector prompt per
eval (every skill name and description, then the user request) to a command such as
`claude -p` or `codex exec -` on stdin, reads the JSON list of skill names it prints,
and reports precision, recall and pass rates. The script never calls an API itself,
so it needs no keys: the judge command uses whatever login it already has.

Standard library only. See evals/README.md for the file format and scoring rules.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVALS = Path("evals") / "triggers.json"
KINDS = ("should", "near-miss", "combo", "none")
REQUIRED_KEYS = {"id", "prompt", "expected", "kind"}
ALLOWED_KEYS = REQUIRED_KEYS | {"notes"}
MIN_SHOULD = 3
MIN_NEAR_MISS = 1
ROUTER = "router"
JSON_LIST_RE = re.compile(r"\[[^\[\]]*\]")


# --------------------------------------------------------------------------- skills


def _frontmatter(text: str) -> dict[str, str]:
    """Read the flat `name` and `description` fields (inline or folded scalars)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        i += 1
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value in {">", "|", ">-", "|-", ">+", "|+"}:
            block = []
            while i < len(lines) and lines[i].strip() != "---" and (not lines[i].strip() or lines[i][:1] in " \t"):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            value = " ".join(block)
        fields[key] = value.strip("\"'")
    return fields


def load_skills(root: Path, include_router: bool = True) -> dict[str, str]:
    """Return {name: description} for skills/**/SKILL.md (and router/SKILL.md)."""
    files = sorted((root / "skills").rglob("SKILL.md")) if (root / "skills").is_dir() else []
    if include_router and (root / "router" / "SKILL.md").is_file():
        files.append(root / "router" / "SKILL.md")
    skills: dict[str, str] = {}
    for path in files:
        fields = _frontmatter(path.read_text(encoding="utf-8"))
        name = fields.get("name") or path.parent.name
        skills[name] = fields.get("description", "")
    return skills


# --------------------------------------------------------------------------- check


def target_of(item: dict) -> str:
    """The skill a should or near-miss prompt is about: the id text before the first dot."""
    return str(item.get("id", "")).split(".", 1)[0]


def check_evals(data: object, skill_names: set[str]) -> tuple[list[str], list[str]]:
    """Return (schema problems, catalog problems); both empty means the file is valid.

    Schema problems make the file unusable. Catalog problems (unknown skill names, too
    few prompts for a skill) depend on which checkout is scored, so judge runs against an
    older checkout can still go ahead.
    """
    if not isinstance(data, list):
        return ["top level must be a JSON list of eval objects"], []

    errors: list[str] = []
    catalog: list[str] = []
    seen: dict[str, int] = {}
    should: dict[str, int] = {name: 0 for name in skill_names}
    near_miss: dict[str, int] = {name: 0 for name in skill_names}

    for index, item in enumerate(data):
        where = f"item {index}"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object")
            continue
        item_id = item.get("id")
        duplicate = False
        if isinstance(item_id, str) and item_id:
            where = f"{item_id!r}"
            duplicate = item_id in seen
            if duplicate:
                errors.append(f"{where}: duplicate id (also item {seen[item_id]})")
            seen.setdefault(item_id, index)
        missing = sorted(REQUIRED_KEYS - item.keys())
        if missing:
            errors.append(f"{where}: missing key(s): {', '.join(missing)}")
        extra = sorted(item.keys() - ALLOWED_KEYS)
        if extra:
            errors.append(f"{where}: unknown key(s): {', '.join(extra)}")
        if "id" in item and (not isinstance(item_id, str) or not item_id.strip()):
            errors.append(f"{where}: 'id' must be a non-empty string")
        if "prompt" in item and (not isinstance(item["prompt"], str) or not item["prompt"].strip()):
            errors.append(f"{where}: 'prompt' must be a non-empty string")
        if "notes" in item and not isinstance(item["notes"], str):
            errors.append(f"{where}: 'notes' must be a string")

        kind = item.get("kind")
        if "kind" in item and kind not in KINDS:
            errors.append(f"{where}: 'kind' must be one of {', '.join(KINDS)}")
            kind = None

        expected = item.get("expected")
        if "expected" in item:
            if not isinstance(expected, list) or not all(isinstance(name, str) for name in expected):
                errors.append(f"{where}: 'expected' must be a list of skill names")
                expected = None
            else:
                if len(set(expected)) != len(expected):
                    errors.append(f"{where}: 'expected' lists a skill twice")
                for name in expected:
                    if name == ROUTER:
                        errors.append(f"{where}: do not expect 'router'; the runner ignores it when scoring")
                    elif name not in skill_names:
                        catalog.append(f"{where}: unknown skill {name!r}")
        if kind is None or expected is None:
            continue

        target = target_of(item)
        if kind in ("should", "near-miss"):
            if "." not in str(item.get("id", "")):
                errors.append(f"{where}: {kind} ids start with the skill name and a dot, like 'audio-design.s1'")
            elif kind == "should" and target not in expected:
                errors.append(f"{where}: a should prompt must expect its own skill {target!r}")
            elif kind == "near-miss" and target in expected:
                errors.append(f"{where}: a near-miss prompt must not expect its own skill {target!r}")
            elif target not in skill_names:
                if kind == "near-miss":
                    catalog.append(f"{where}: id names unknown skill {target!r}")
            elif duplicate:
                pass  # already reported; a repeated id must not count towards coverage
            elif kind == "should":
                should[target] += 1
            else:
                near_miss[target] += 1
        elif kind == "combo" and len(expected) < 2:
            errors.append(f"{where}: a combo prompt must expect at least 2 skills")
        elif kind == "none" and expected:
            errors.append(f"{where}: a none prompt must have an empty 'expected' list")

    for name in sorted(skill_names):
        if should[name] < MIN_SHOULD:
            catalog.append(f"skill {name!r}: {should[name]} should prompt(s), needs at least {MIN_SHOULD}")
        if near_miss[name] < MIN_NEAR_MISS:
            catalog.append(f"skill {name!r}: {near_miss[name]} near-miss prompt(s), needs at least {MIN_NEAR_MISS}")
    return errors, catalog


# --------------------------------------------------------------------------- judge


def selector_prompt(skills: dict[str, str], request: str) -> str:
    catalog = "\n".join(f"- {name}: {description}" for name, description in sorted(skills.items()))
    return (
        "You are deciding which agent skills to load before starting work on a request.\n"
        "Each installed skill is listed below with its description. Pick every skill whose\n"
        "description fits the request, or none if nothing fits. Do not answer the request.\n\n"
        f"Installed skills:\n{catalog}\n\n"
        "Request:\n"
        "----- request start -----\n"
        f"{request}\n"
        "----- request end -----\n\n"
        'Reply with only a JSON list of skill names, for example ["skill-a", "skill-b"] or [].\n'
    )


def parse_selection(output: str) -> list[str] | None:
    """Return the last JSON list of strings in the judge output, or None."""
    for candidate in reversed(JSON_LIST_RE.findall(output)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and all(isinstance(name, str) for name in value):
            return sorted({name.strip().lstrip("$").lower() for name in value if name.strip()})
    return None


def run_judge(argv: list[str], prompt: str, timeout: float, retries: int) -> tuple[list[str] | None, str]:
    """Run the judge once (plus retries); return (selection, error message)."""
    error = ""
    for _ in range(retries + 1):
        try:
            result = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return None, f"judge command not found: {argv[0]}"
        except subprocess.TimeoutExpired:
            error = f"judge timed out after {timeout:g}s"
            continue
        if result.returncode != 0:
            error = f"judge exited {result.returncode}: {result.stderr.strip()[-300:]}"
            continue
        selection = parse_selection(result.stdout)
        if selection is not None:
            return selection, ""
        error = f"no JSON list in judge output: {result.stdout.strip()[-300:]!r}"
    return None, error


# --------------------------------------------------------------------------- scoring


def score_item(item: dict, selection: list[str]) -> dict:
    """Score one answered eval. `router` is ignored on both sides."""
    chosen = {name for name in selection if name != ROUTER}
    expected = set(item["expected"])
    kind = item["kind"]
    target = target_of(item)
    if kind == "none":
        passed = not chosen
    elif kind == "near-miss":
        passed = target not in chosen and expected <= chosen
    else:
        passed = expected <= chosen
    return {
        "id": item["id"],
        "kind": kind,
        "expected": sorted(expected),
        "selected": sorted(chosen),
        "missed": sorted(expected - chosen),
        "extra": sorted(chosen - expected),
        "passed": passed,
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarize(results: list[dict], errors: list[dict], worst: int) -> dict:
    tp = sum(len(set(r["expected"]) & set(r["selected"])) for r in results)
    fp = sum(len(r["extra"]) for r in results)
    fn = sum(len(r["missed"]) for r in results)

    kinds: dict[str, dict] = {}
    for kind in KINDS:
        rows = [r for r in results if r["kind"] == kind]
        passed = sum(r["passed"] for r in rows)
        kinds[kind] = {"passed": passed, "total": len(rows), "rate": _ratio(passed, len(rows))}
    passed_all = sum(r["passed"] for r in results)
    kinds["all"] = {"passed": passed_all, "total": len(results), "rate": _ratio(passed_all, len(results))}

    per_skill: dict[str, dict] = {}

    def row(name: str) -> dict:
        return per_skill.setdefault(name, {"tp": 0, "fp": 0, "fn": 0, "missed_ids": [], "false_ids": []})

    for r in results:
        for name in set(r["expected"]) & set(r["selected"]):
            row(name)["tp"] += 1
        for name in r["missed"]:
            row(name)["fn"] += 1
            row(name)["missed_ids"].append(r["id"])
        for name in r["extra"]:
            row(name)["fp"] += 1
            row(name)["false_ids"].append(r["id"])
    for stats in per_skill.values():
        stats["precision"] = _ratio(stats["tp"], stats["tp"] + stats["fp"])
        stats["recall"] = _ratio(stats["tp"], stats["tp"] + stats["fn"])
        stats["f1"] = _ratio(2 * stats["tp"], 2 * stats["tp"] + stats["fp"] + stats["fn"]) or 0.0

    ranked = sorted(
        (name for name, stats in per_skill.items() if stats["fp"] or stats["fn"]),
        key=lambda name: (per_skill[name]["f1"], -(per_skill[name]["fp"] + per_skill[name]["fn"]), name),
    )
    return {
        "answered": len(results),
        "judge_errors": len(errors),
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "kinds": kinds,
        "worst_skills": [{"skill": name, **per_skill[name]} for name in ranked[:worst]],
        "skills": dict(sorted(per_skill.items())),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def print_report(summary: dict, results: list[dict], errors: list[dict], judge: str) -> None:
    print(f"Trigger evals: {summary['answered']} answered, {summary['judge_errors']} judge error(s); judge: {judge}")
    print(
        f"Precision {_pct(summary['precision'])}  Recall {_pct(summary['recall'])}  "
        f"(TP {summary['true_positives']}, FP {summary['false_positives']}, FN {summary['false_negatives']})"
    )
    print("\nPass rate by kind:")
    for kind, stats in summary["kinds"].items():
        print(f"  {kind:<10} {stats['passed']:>4}/{stats['total']:<4} {_pct(stats['rate'])}")
    if summary["worst_skills"]:
        print("\nWorst skills (lowest F1 first):")
        for stats in summary["worst_skills"]:
            print(
                f"  {stats['skill']:<34} F1 {stats['f1']:.2f}  missed {stats['fn']}  false {stats['fp']}"
                + (f"  missed: {', '.join(stats['missed_ids'])}" if stats["missed_ids"] else "")
                + (f"  false: {', '.join(stats['false_ids'])}" if stats["false_ids"] else "")
            )
    failed = [r for r in results if not r["passed"]]
    if failed:
        print("\nFailed prompts:")
        for r in failed:
            print(f"  {r['id']} [{r['kind']}] expected {r['expected']} got {r['selected']}")
    for error in errors:
        print(f"ERROR {error['id']}: {error['error']}")


# --------------------------------------------------------------------------- CLI


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the trigger eval file offline, or score skill descriptions with a judge command.",
    )
    parser.add_argument("--evals", type=Path, help=f"eval file (default: {DEFAULT_EVALS.as_posix()} in --root)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="checkout whose skills/ and router/ descriptions are used (default: this repo)")
    parser.add_argument("--check", action="store_true", help="validate the eval file offline and exit")
    parser.add_argument("--allow-missing", action="store_true",
                        help="with --check, pass when the eval file does not exist yet")
    parser.add_argument("--judge-cmd", help="command that reads the selector prompt on stdin, e.g. 'claude -p'")
    parser.add_argument("--without-router", action="store_true", help="leave the router out of the selector prompt")
    parser.add_argument("--kind", choices=KINDS, action="append", help="only run this kind (repeatable)")
    parser.add_argument("--limit", type=int, help="only run the first N evals (after --kind)")
    parser.add_argument("--jobs", type=int, default=1, help="judge calls to run at once (default: 1)")
    parser.add_argument("--timeout", type=float, default=300, help="seconds per judge call (default: 300)")
    parser.add_argument("--retries", type=int, default=1, help="retries per failed judge call (default: 1)")
    parser.add_argument("--worst", type=int, default=10, help="how many worst skills to list (default: 10)")
    parser.add_argument("--print-prompt", metavar="ID", help="print the selector prompt for one eval id and exit")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    args = parser.parse_args(argv)
    if not (args.check or args.judge_cmd or args.print_prompt):
        parser.error("choose --check, --judge-cmd or --print-prompt")
    if args.jobs < 1 or args.retries < 0 or args.worst < 0 or (args.limit is not None and args.limit < 0):
        parser.error("--jobs must be >= 1; --retries, --worst and --limit must be >= 0")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    evals_path = (args.evals or root / DEFAULT_EVALS).resolve()

    if not evals_path.is_file():
        if args.check and args.allow_missing and not args.judge_cmd:
            print(f"No eval file at {evals_path}; nothing to check.")
            return 0
        print(f"Eval file not found: {evals_path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"Cannot read {evals_path}: {exc}", file=sys.stderr)
        return 2

    all_skills = load_skills(root)
    if not all_skills:
        print(f"No skills found under {root / 'skills'}", file=sys.stderr)
        return 2
    schema_problems, catalog_problems = check_evals(data, {name for name in all_skills if name != ROUTER})
    # --check is strict about both. A judge run only needs a well-formed file, so it can
    # score an older checkout that lacks some skills (they count as missed).
    problems = schema_problems + catalog_problems if args.check else schema_problems
    if problems:
        if args.json and args.check:
            print(json.dumps({"file": str(evals_path), "valid": False, "errors": problems}, indent=2))
        else:
            print(f"FAILED: {evals_path} has {len(problems)} problem(s):")
            for problem in problems:
                print(f"  - {problem}")
        return 1
    for problem in catalog_problems:
        print(f"WARNING: {problem}", file=sys.stderr)
    if args.check and not args.judge_cmd and not args.print_prompt:
        counts = {kind: sum(1 for item in data if item["kind"] == kind) for kind in KINDS}
        if args.json:
            print(json.dumps({"file": str(evals_path), "valid": True, "evals": len(data), "kinds": counts}, indent=2))
        else:
            detail = ", ".join(f"{counts[kind]} {kind}" for kind in KINDS)
            print(f"{evals_path.name}: {len(data)} evals OK ({detail}) for {len(all_skills) - (ROUTER in all_skills)} skills.")
        return 0

    selector_skills = {n: d for n, d in all_skills.items() if not (args.without_router and n == ROUTER)}
    if args.print_prompt:
        item = next((item for item in data if item["id"] == args.print_prompt), None)
        if item is None:
            print(f"No eval with id {args.print_prompt!r}", file=sys.stderr)
            return 2
        print(selector_prompt(selector_skills, item["prompt"]), end="")
        return 0

    items = [item for item in data if not args.kind or item["kind"] in args.kind]
    if args.limit is not None:
        items = items[: args.limit]
    judge_argv = shlex.split(args.judge_cmd)
    if not judge_argv:
        print("--judge-cmd is empty", file=sys.stderr)
        return 2

    def answer(item: dict) -> tuple[dict, list[str] | None, str]:
        selection, error = run_judge(judge_argv, selector_prompt(selector_skills, item["prompt"]), args.timeout, args.retries)
        return item, selection, error

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        answers = list(pool.map(answer, items))

    results: list[dict] = []
    errors: list[dict] = []
    for item, selection, error in answers:
        if selection is None:
            errors.append({"id": item["id"], "error": error})
        else:
            results.append(score_item(item, selection))
    summary = summarize(results, errors, args.worst)

    if args.json:
        report = {
            "file": str(evals_path),
            "root": str(root),
            "judge": args.judge_cmd,
            "summary": summary,
            "results": results,
            "errors": errors,
        }
        print(json.dumps(report, indent=2))
    else:
        print_report(summary, results, errors, args.judge_cmd)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
