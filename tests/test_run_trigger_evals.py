"""End-to-end tests for scripts/run-trigger-evals.py with a fake judge command."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-trigger-evals.py"
SPEC = importlib.util.spec_from_file_location("run_trigger_evals", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
evals = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evals)

# A small sample eval file: two skills, each with 3 should prompts and 1 near-miss.
SAMPLE = [
    {"id": "alpha-skill.s1", "prompt": "alpha one", "expected": ["alpha-skill"], "kind": "should", "notes": ""},
    {"id": "alpha-skill.s2", "prompt": "alpha two", "expected": ["alpha-skill"], "kind": "should"},
    {"id": "alpha-skill.s3", "prompt": "alpha three", "expected": ["alpha-skill", "beta-skill"], "kind": "should"},
    {"id": "alpha-skill.nm", "prompt": "looks like alpha", "expected": ["beta-skill"], "kind": "near-miss"},
    {"id": "beta-skill.s1", "prompt": "beta one", "expected": ["beta-skill"], "kind": "should"},
    {"id": "beta-skill.s2", "prompt": "beta two", "expected": ["beta-skill"], "kind": "should"},
    {"id": "beta-skill.s3", "prompt": "beta three", "expected": ["beta-skill"], "kind": "should"},
    {"id": "beta-skill.nm", "prompt": "looks like beta", "expected": [], "kind": "near-miss"},
    {"id": "combo.01", "prompt": "alpha and beta", "expected": ["alpha-skill", "beta-skill"], "kind": "combo"},
    {"id": "none.01", "prompt": "write a sql query", "expected": [], "kind": "none"},
]

# The fake judge answers from a {request: output} map, so each test controls every reply.
FAKE_JUDGE = r'''
import json, sys
prompt = sys.stdin.read()
assert "- alpha-skill: Alpha description." in prompt, prompt
request = prompt.split("----- request start -----\n", 1)[1].split("\n----- request end -----", 1)[0]
answers = json.load(open(sys.argv[1], encoding="utf-8"))
reply = answers.get(request, "[]")
if reply == "FAIL":
    sys.stderr.write("judge broke")
    sys.exit(3)
print(reply)
'''


class TriggerEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name, description in (("alpha-skill", "Alpha description."), ("beta-skill", "Beta description.")):
            path = self.root / "skills" / "disciplines" / name / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n# {name}\n", encoding="utf-8")
        router = self.root / "router" / "SKILL.md"
        router.parent.mkdir()
        router.write_text("---\nname: router\ndescription: Routes requests.\n---\n", encoding="utf-8")
        self.judge = self.root / "fake_judge.py"
        self.judge.write_text(FAKE_JUDGE, encoding="utf-8")
        self.answers = self.root / "answers.json"

    def write_evals(self, data: object) -> Path:
        path = self.root / "evals" / "triggers.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = evals.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def judge_cmd(self, answers: dict[str, str]) -> str:
        self.answers.write_text(json.dumps(answers), encoding="utf-8")
        return shlex.join([sys.executable, str(self.judge), str(self.answers)])

    # ------------------------------------------------------------------ --check

    def test_sample_file_passes_check(self) -> None:
        self.write_evals(SAMPLE)

        code, out, _ = self.run_cli("--check")

        self.assertEqual(code, 0, out)
        self.assertIn("10 evals OK (6 should, 2 near-miss, 1 combo, 1 none) for 2 skills", out)

    def test_missing_file_passes_only_with_allow_missing(self) -> None:
        code, out, _ = self.run_cli("--check", "--allow-missing")
        missing_code, _, err = self.run_cli("--check")

        self.assertEqual(code, 0)
        self.assertIn("nothing to check", out)
        self.assertEqual(missing_code, 2)
        self.assertIn("not found", err)

    def test_check_reports_schema_and_coverage_problems(self) -> None:
        bad = [dict(item) for item in SAMPLE]
        bad[1]["id"] = "alpha-skill.s1"                      # duplicate id
        bad[4]["expected"] = ["gamma-skill", "beta-skill"]   # unknown skill
        bad[7] = {"id": "beta-skill.nm", "prompt": "x", "expected": ["beta-skill"], "kind": "near-miss"}
        bad[8]["expected"] = ["alpha-skill"]                 # combo needs 2
        bad[9]["kind"] = "maybe"                             # bad kind
        bad.append({"id": "router.s1", "prompt": "route", "expected": ["router"], "kind": "should", "extra": 1})
        self.write_evals(bad)

        code, out, _ = self.run_cli("--check", "--json")
        report = json.loads(out)
        problems = "\n".join(report["errors"])

        self.assertEqual(code, 1)
        self.assertFalse(report["valid"])
        for text in (
            "'alpha-skill.s1': duplicate id",
            "'beta-skill.s1': unknown skill 'gamma-skill'",
            "'beta-skill.nm': a near-miss prompt must not expect its own skill 'beta-skill'",
            "'combo.01': a combo prompt must expect at least 2 skills",
            "'none.01': 'kind' must be one of",
            "'router.s1': unknown key(s): extra",
            "'router.s1': do not expect 'router'",
            "skill 'alpha-skill': 2 should prompt(s), needs at least 3",
            "skill 'beta-skill': 0 near-miss prompt(s), needs at least 1",
        ):
            self.assertIn(text, problems)

    def test_top_level_must_be_a_list(self) -> None:
        self.write_evals({"prompts": SAMPLE})

        code, out, _ = self.run_cli("--check")

        self.assertEqual(code, 1)
        self.assertIn("top level must be a JSON list", out)

    # ------------------------------------------------------------------ judge

    def test_perfect_judge_scores_full_marks(self) -> None:
        self.write_evals(SAMPLE)
        answers = {item["prompt"]: json.dumps(item["expected"]) for item in SAMPLE}
        answers["alpha one"] = '["alpha-skill", "router"]'  # router is ignored

        code, out, _ = self.run_cli("--judge-cmd", self.judge_cmd(answers), "--json")
        summary = json.loads(out)["summary"]

        self.assertEqual(code, 0, out)
        self.assertEqual(summary["precision"], 1.0)
        self.assertEqual(summary["recall"], 1.0)
        self.assertEqual(summary["kinds"]["all"], {"passed": 10, "total": 10, "rate": 1.0})
        self.assertEqual(summary["worst_skills"], [])

    def test_mistakes_lower_precision_recall_and_name_worst_skill(self) -> None:
        self.write_evals(SAMPLE)
        answers = {item["prompt"]: json.dumps(item["expected"]) for item in SAMPLE}
        answers.update(
            {
                "alpha two": "[]",                                          # miss
                "looks like alpha": 'Sure.\n```json\n["alpha-skill"]\n```',  # near-miss stolen, beta missed
                "write a sql query": '["alpha-skill"]',                     # false trigger
            }
        )

        code, out, _ = self.run_cli("--judge-cmd", self.judge_cmd(answers), "--json", "--jobs", "3")
        report = json.loads(out)
        summary = report["summary"]

        self.assertEqual(code, 0)
        self.assertEqual((summary["true_positives"], summary["false_positives"], summary["false_negatives"]), (8, 2, 2))
        self.assertEqual(summary["kinds"]["should"]["passed"], 5)
        self.assertEqual(summary["kinds"]["near-miss"], {"passed": 1, "total": 2, "rate": 0.5})
        self.assertEqual(summary["kinds"]["none"]["passed"], 0)
        self.assertEqual(summary["worst_skills"][0]["skill"], "alpha-skill")
        self.assertEqual(summary["worst_skills"][0]["false_ids"], ["alpha-skill.nm", "none.01"])
        self.assertEqual(summary["worst_skills"][0]["missed_ids"], ["alpha-skill.s2"])

    def test_text_report_and_judge_errors(self) -> None:
        self.write_evals(SAMPLE)
        answers = {item["prompt"]: json.dumps(item["expected"]) for item in SAMPLE}
        answers["beta one"] = "FAIL"
        answers["beta two"] = "I would pick beta."

        code, out, _ = self.run_cli("--judge-cmd", self.judge_cmd(answers), "--retries", "0")

        self.assertEqual(code, 1)
        self.assertIn("8 answered, 2 judge error(s)", out)
        self.assertIn("Pass rate by kind:", out)
        self.assertIn("ERROR beta-skill.s1: judge exited 3: judge broke", out)
        self.assertIn("ERROR beta-skill.s2: no JSON list in judge output", out)

    def test_kind_and_limit_filters(self) -> None:
        self.write_evals(SAMPLE)

        code, out, _ = self.run_cli("--judge-cmd", self.judge_cmd({}), "--kind", "none", "--kind", "combo", "--json")
        summary = json.loads(out)["summary"]

        self.assertEqual(code, 0)
        self.assertEqual(summary["answered"], 2)
        self.assertEqual(summary["kinds"]["none"]["passed"], 1)
        self.assertEqual(summary["kinds"]["combo"]["passed"], 0)

        code, out, _ = self.run_cli("--judge-cmd", self.judge_cmd({}), "--limit", "3", "--json")
        self.assertEqual(json.loads(out)["summary"]["answered"], 3)

    def test_judge_run_on_older_checkout_warns_about_unknown_skills(self) -> None:
        extra = SAMPLE + [{"id": "combo.02", "prompt": "new", "expected": ["alpha-skill", "new-skill"], "kind": "combo"}]
        self.write_evals(extra)

        code, out, err = self.run_cli("--judge-cmd", self.judge_cmd({"new": '["alpha-skill"]'}), "--kind", "combo", "--json")

        self.assertEqual(code, 0, out)
        self.assertIn("WARNING: 'combo.02': unknown skill 'new-skill'", err)
        self.assertEqual(json.loads(out)["summary"]["false_negatives"], 3)

    def test_print_prompt_and_without_router(self) -> None:
        self.write_evals(SAMPLE)

        code, out, _ = self.run_cli("--print-prompt", "none.01")
        _, without, _ = self.run_cli("--print-prompt", "none.01", "--without-router")

        self.assertEqual(code, 0)
        self.assertIn("- alpha-skill: Alpha description.\n- beta-skill: Beta description.\n- router: Routes", out)
        self.assertIn("write a sql query", out)
        self.assertNotIn("- router:", without)

    def test_parse_selection_takes_the_last_json_list(self) -> None:
        self.assertEqual(evals.parse_selection('Options [1, 2]. Answer: ["$Beta-Skill", "alpha-skill"]'), ["alpha-skill", "beta-skill"])
        self.assertIsNone(evals.parse_selection("no list here"))


if __name__ == "__main__":
    unittest.main()
