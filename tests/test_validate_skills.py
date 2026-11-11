"""Regression tests for scripts/validate-skills.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-skills.py"
SPEC = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validate_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_skills)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.root_patch = patch.object(validate_skills, "REPO_ROOT", self.repo_root)
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temp_dir.cleanup()

    def write_skill(
        self,
        category: str,
        name: str,
        frontmatter: str | None = None,
        body: str = "# Test\n\n## Gotchas\n\n- A fixture gotcha.\n",
    ) -> Path:
        path = self.repo_root / "skills" / category / name / "SKILL.md"
        path.parent.mkdir(parents=True)
        fields = frontmatter or (
            f"name: {name}\n"
            "description: Handles test fixtures. Use when validating a test skill. "
            "Not for real skills (use other-skill)."
        )
        path.write_text(f"---\n{fields}\n---\n\n{body}", encoding="utf-8")
        return path

    def test_valid_two_field_frontmatter_passes(self) -> None:
        path = self.write_skill("disciplines", "test-skill")

        errors, warnings = validate_skills.validate_file(path)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_extra_frontmatter_is_rejected(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            "name: test-skill\n"
            "description: Handles fixtures. Use when testing portability.\n"
            "compatibility: Python 3.12",
        )

        errors, _ = validate_skills.validate_file(path)

        self.assertTrue(any("non-portable frontmatter field(s): compatibility" in error for error in errors))

    def test_description_limit_and_xml_are_enforced(self) -> None:
        oversized = self.write_skill(
            "first",
            "large-description",
            f"name: large-description\ndescription: {'x' * 1025}",
        )
        xml = self.write_skill(
            "second",
            "xml-description",
            "name: xml-description\ndescription: Handles fixtures <example>. Use when testing XML.",
        )

        oversized_errors, _ = validate_skills.validate_file(oversized)
        xml_errors, _ = validate_skills.validate_file(xml)

        self.assertTrue(any("max 1024" in error for error in oversized_errors))
        self.assertTrue(any("angle brackets" in error for error in xml_errors))

    def test_generic_type_syntax_is_allowed_in_the_body(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            body="# Test\n\nCall `GetNode<T>()` in C# code.\n",
        )

        errors, _ = validate_skills.validate_file(path)

        self.assertEqual(errors, [])

    def test_duplicate_names_are_rejected_repo_wide(self) -> None:
        first = self.write_skill("first", "same-name")
        second = self.write_skill("second", "same-name")

        errors = validate_skills.validate_unique_names([first, second])

        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate skill name 'same-name'", errors[0])

    def test_broken_bundled_resource_path_is_rejected(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            body="# Test\n\nRead `references/missing.md`.\n",
        )

        errors, _ = validate_skills.validate_file(path)

        self.assertTrue(any("does not resolve" in error for error in errors))

    def test_link_like_code_in_fences_is_not_a_link(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            body="# Test\n\n```lua\nif screen[name] then screen[name](screen, ...) end\n```\n\n[Missing](missing.md)\n",
        )

        errors, _ = validate_skills.validate_file(path)

        self.assertEqual(errors, ["skills/disciplines/test-skill/SKILL.md: local resource link does not resolve: 'missing.md'"])

    def test_openai_ui_metadata_is_checked(self) -> None:
        path = self.write_skill("disciplines", "test-skill")
        agents = path.parent / "agents"
        agents.mkdir()
        (agents / "openai.yaml").write_text(
            'interface:\n'
            '  display_name: "Test Skill"\n'
            '  short_description: "Validate fixture metadata cleanly"\n'
            '  default_prompt: "Use this helper for the fixture."\n',
            encoding="utf-8",
        )

        errors, _ = validate_skills.validate_file(path)

        self.assertTrue(any("default_prompt must mention $test-skill" in error for error in errors))

    def test_repository_markdown_links_are_checked_outside_code_fences(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text(
            "[missing](docs/missing.md)\n\n```md\n[example](not-real.md)\n```\n",
            encoding="utf-8",
        )

        errors = validate_skills.validate_markdown_links()

        self.assertEqual(len(errors), 1)
        self.assertIn("docs/missing.md", errors[0])

    def test_marketplace_requires_strict_false_for_explicit_paths(self) -> None:
        skill = self.write_skill("godot", "test-skill")
        router = self.repo_root / "router" / "SKILL.md"
        router.parent.mkdir()
        router.write_text(
            "---\nname: router\ndescription: Routes fixtures. Use when selecting a test skill.\n---\n",
            encoding="utf-8",
        )
        plugins = []
        for name in (
            "gamedev",
            "router",
            "godot",
            "unity",
            "unreal",
            "ebitengine",
            "web-engines",
            "other-engines",
            "disciplines",
            "genres",
            "workflows",
        ):
            paths: list[str] = []
            if name == "gamedev":
                paths = ["./skills/godot/test-skill", "./router"]
            elif name == "router":
                paths = ["./router"]
            elif name == "godot":
                paths = ["./skills/godot/test-skill"]
            plugin = {"name": name, "source": "./", "strict": False, "skills": paths}
            plugins.append(plugin)
        plugins[0].pop("strict")
        manifest = self.repo_root / ".claude-plugin" / "marketplace.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"plugins": plugins}), encoding="utf-8")

        errors = validate_skills.validate_marketplace([skill, router])

        self.assertTrue(any("'gamedev' must set strict=false" in error for error in errors))

    def test_checkout_folder_named_like_a_category_passes_bundle_check(self) -> None:
        # A checkout folder called "godot" makes router/SKILL.md's grandparent
        # folder name "godot"; the router must still not count as a Godot skill.
        root = self.repo_root / "godot"
        root.mkdir()
        with patch.object(validate_skills, "REPO_ROOT", root):
            skill = root / "skills" / "godot" / "test-skill" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: test-skill\ndescription: Handles fixtures. Use when testing.\n---\n",
                encoding="utf-8",
            )
            router = root / "router" / "SKILL.md"
            router.parent.mkdir()
            router.write_text(
                "---\nname: router\ndescription: Routes fixtures. Use when selecting a test skill.\n---\n",
                encoding="utf-8",
            )
            plugins = []
            for name in (
                "gamedev", "router", "godot", "unity", "unreal", "ebitengine",
                "web-engines", "other-engines", "disciplines", "genres", "workflows",
            ):
                paths = {
                    "gamedev": ["./skills/godot/test-skill", "./router"],
                    "router": ["./router"],
                    "godot": ["./skills/godot/test-skill"],
                }.get(name, [])
                plugins.append({"name": name, "source": "./", "strict": False, "skills": paths})
            manifest = root / ".claude-plugin" / "marketplace.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({"plugins": plugins}), encoding="utf-8")

            errors = validate_skills.validate_marketplace([skill, router])

        self.assertFalse(any("does not exactly match" in error for error in errors), errors)

    def write_reference(self, skill: Path, name: str, text: str) -> Path:
        path = skill.parent / "references" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_not_for_clause_is_a_warning(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            "name: test-skill\ndescription: Handles fixtures. Use when validating a test skill.",
        )

        errors, warnings = validate_skills.validate_file(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("no 'Not for ...' clause", warnings[0])

    def test_router_needs_no_not_for_clause(self) -> None:
        router = self.repo_root / "router" / "SKILL.md"
        router.parent.mkdir()
        router.write_text(
            "---\nname: router\ndescription: Routes fixtures. Use when selecting a test skill.\n---\n\n"
            "# Router\n\n## Gotchas\n\n- A fixture gotcha.\n",
            encoding="utf-8",
        )

        errors, warnings = validate_skills.validate_file(router)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_not_for_clause_matches_any_case(self) -> None:
        path = self.write_skill(
            "disciplines",
            "test-skill",
            "name: test-skill\ndescription: >\n  Handles fixtures. Use when testing,\n  not for real work.",
        )

        _, warnings = validate_skills.validate_file(path)

        self.assertEqual(warnings, [])

    def test_missing_gotchas_heading_is_a_warning(self) -> None:
        for body in ("# Test\n\n## Pitfalls\n\n- old name\n", "# Test\n\n```md\n## Gotchas\n```\n"):
            with self.subTest(body=body):
                path = self.write_skill("disciplines", f"test-skill-{len(body)}", body=body)

                errors, warnings = validate_skills.validate_file(path)

                self.assertEqual(errors, [])
                self.assertEqual([w.split(": ", 1)[1] for w in warnings], ["no '## Gotchas' heading"])

    def test_long_reference_needs_a_contents_list(self) -> None:
        path = self.write_skill("disciplines", "test-skill")
        filler = "".join(f"line {i}\n" for i in range(110))
        self.write_reference(path, "long.md", "# Long\n\n" + filler)
        for name, opening in (
            ("heading.md", "# Ok\n\n## Contents\n\n- Setup\n- Usage\n\n"),
            ("inline.md", "# Ok\n\nContents: setup · usage · gotchas\n\n"),
            ("anchors.md", "# Ok\n\n- [Setup](#setup)\n- [Usage](#usage)\n- [Gotchas](#gotchas)\n\n"),
        ):
            self.write_reference(path, name, opening + filler)
        self.write_reference(path, "short.md", "# Short\n\n" + "x\n" * 90)

        errors, warnings = validate_skills.validate_file(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("references/long.md: 112 lines but no contents list", warnings[0])

    def test_reference_linking_to_another_reference_is_a_warning(self) -> None:
        path = self.write_skill("disciplines", "test-skill", body="# Test\n\n## Gotchas\n\n[A](references/a.md) [B](references/b.md)\n")
        self.write_reference(path, "a.md", "# A\n\nSee [B](b.md#part) and [self](#a) and [skill](../SKILL.md).\n\n```md\n[c](c.md)\n```\n")
        self.write_reference(path, "b.md", "# B\n")

        errors, warnings = validate_skills.validate_file(path)

        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("references/a.md: links to another reference (skills/disciplines/test-skill/references/b.md)", warnings[0])

    def run_main(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        empty: list[str] = []
        with patch.object(validate_skills, "find_skill_files", return_value=[self.warned_skill]), \
                patch.object(validate_skills, "validate_unique_names", return_value=empty), \
                patch.object(validate_skills, "validate_json_assets", return_value=empty), \
                patch.object(validate_skills, "validate_markdown_links", return_value=empty), \
                patch.object(validate_skills, "validate_marketplace", return_value=empty), \
                patch.object(validate_skills, "validate_router_and_catalog", return_value=empty), \
                contextlib.redirect_stdout(output):
            code = validate_skills.main(list(args))
        return code, output.getvalue()

    def test_warnings_print_and_only_fail_with_strict(self) -> None:
        self.warned_skill = self.write_skill(
            "disciplines", "test-skill", "name: test-skill\ndescription: Handles fixtures. Use when testing.", body="# Test\n"
        )

        code, output = self.run_main()
        strict_code, strict_output = self.run_main("--strict")

        self.assertEqual(code, 0, output)
        self.assertIn("WARNING: skills/disciplines/test-skill/SKILL.md: no '## Gotchas' heading", output)
        self.assertIn("2 warning(s).", output)
        self.assertIn("All checks passed.", output)
        self.assertEqual(strict_code, 1, strict_output)
        self.assertIn("warnings are errors with --strict", strict_output)


if __name__ == "__main__":
    unittest.main()
