#!/usr/bin/env python3
"""Validate a task's memory/ directory against the experience-memory format.

    python3 check_memory.py MEMORY_DIR
    python3 check_memory.py MEMORY_DIR --json

MEMORY_DIR is the session's `memory/` folder (TIPS.md, INDEX.md, skills/). The
checker reads files as data and does not import or run remembered code. It
exits 1 when anything breaks the format. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONFIRMATIONS = ("observed", "task-confirmed")
SKILL_REF = re.compile(r"skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md")
TIPS_COLUMNS = (
    "Task phase",
    "Preconditions",
    "What worked",
    "Visible effect",
    "Evidence",
)
INDEX_COLUMNS = ("Skill", "Tags", "Confirmation", "Last confirmed")
LEARNED_BULLETS = (
    "Applies when",
    "Avoid when",
    "Executed action",
    "Pose recipe",
    "Actions",
    "Expected effect",
    "Recovery",
)
EXAMPLE_KEYS = (
    "task",
    "episode_or_date",
    "confirmation",
    "frames",
    "executed_action",
    "pose_recipe",
    "point_reacquisition",
    "observed_effect",
)
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


@dataclass(frozen=True)
class Issue:
    path: str
    message: str
    line: int | None = None

    def render(self) -> str:
        if self.line is None:
            return f"{self.path}: {self.message}"
        return f"{self.path}:{self.line}: {self.message}"


def parse_frontmatter(text: str) -> dict[str, str] | None:
    match = FRONTMATTER.match(text)
    if not match:
        return None
    fields: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def parse_tables(text: str) -> list[list[tuple[int, list[str]]]]:
    """Return markdown tables as lists of (1-based line number, cells).

    Separator rows are dropped. The first row of each table is the header.
    """
    tables: list[list[tuple[int, list[str]]]] = []
    current: list[tuple[int, list[str]]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line.startswith("|"):
            if current:
                tables.append(current)
                current = []
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell or "---") for cell in cells):
            continue
        current.append((lineno, cells))
    if current:
        tables.append(current)
    return tables


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _issues_for_table(
    path: str,
    rows: list[tuple[int, list[str]]],
    expected: tuple[str, ...],
    source: str,
) -> list[Issue]:
    issues: list[Issue] = []
    if not rows:
        issues.append(Issue(path, f"{source} is empty"))
        return issues
    header_line, header = rows[0]
    if header != list(expected):
        issues.append(
            Issue(
                path,
                f"{source} columns must be {' | '.join(expected)} (got {' | '.join(header)})",
                header_line,
            )
        )
        return issues
    for line, row in rows[1:]:
        if len(row) != len(expected):
            issues.append(
                Issue(
                    path,
                    f"row has {len(row)} cells, expected {len(expected)}",
                    line,
                )
            )
            continue
        for name, cell in zip(expected, row):
            if not cell or cell in {"-", "—", "TODO", "tbd", "TBD"}:
                issues.append(Issue(path, f"{name} is empty", line))
    return issues


def check_tips(root: Path, path: Path) -> list[Issue]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = _rel(root, path)
    tables = parse_tables(text)
    if not tables:
        return [Issue(rel, "must contain a markdown table with the tip columns")]
    issues: list[Issue] = []
    for rows in tables:
        issues.extend(_issues_for_table(rel, rows, TIPS_COLUMNS, "TIPS.md"))
    return issues


def check_index(root: Path, path: Path) -> tuple[list[Issue], dict[str, tuple[str, str, int]]]:
    """Return issues and a map slug -> (confirmation, last_confirmed, line)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = _rel(root, path)
    tables = parse_tables(text)
    if not tables:
        return [Issue(rel, "must contain a markdown table of learned skills")], {}
    issues: list[Issue] = []
    listed: dict[str, tuple[str, str, int]] = {}
    for rows in tables:
        issues.extend(_issues_for_table(rel, rows, INDEX_COLUMNS, "INDEX.md"))
        if not rows or rows[0][1] != list(INDEX_COLUMNS):
            continue
        for line, row in rows[1:]:
            if len(row) != 4:
                continue
            skill_cell, _tags, confirmation, last = row
            confirmation = confirmation.strip("`")
            match = SKILL_REF.search(skill_cell)
            if not match:
                issues.append(
                    Issue(
                        rel,
                        "Skill must be a `skills/<slug>/SKILL.md` path",
                        line,
                    )
                )
                continue
            slug = match.group(1)
            if slug in listed:
                issues.append(Issue(rel, f"duplicate row for {slug}", line))
            listed[slug] = (confirmation, last, line)
            if confirmation not in CONFIRMATIONS:
                issues.append(
                    Issue(
                        rel,
                        f"Confirmation must be {' or '.join(CONFIRMATIONS)} (got {confirmation!r})",
                        line,
                    )
                )
    return issues, listed


def _bullet_value(text: str, label: str) -> str | None:
    pattern = rf"^[-*]\s+\*?\*?{re.escape(label)}\*?\*?:\s*(.*)$"
    match = re.search(pattern, text, re.M)
    if not match:
        return None
    return match.group(1).strip()


def check_learned_skill(root: Path, folder: Path) -> list[Issue]:
    slug = folder.name
    rel_dir = _rel(root, folder)
    issues: list[Issue] = []
    if not SLUG.match(slug):
        issues.append(
            Issue(
                rel_dir,
                "folder name must be lowercase words joined by hyphens",
            )
        )
    skill_path = folder / "SKILL.md"
    evidence_path = folder / "evidence.json"
    if not skill_path.is_file():
        issues.append(Issue(rel_dir, "SKILL.md is missing"))
        return issues
    text = skill_path.read_text(encoding="utf-8", errors="replace")
    rel_skill = _rel(root, skill_path)
    meta = parse_frontmatter(text)
    if meta is None:
        issues.append(Issue(rel_skill, "must begin with --- frontmatter ---"))
        return issues
    expected_name = f"learned-{slug}"
    name = meta.get("name", "")
    if not name:
        issues.append(Issue(rel_skill, "frontmatter needs name"))
    elif name != expected_name:
        issues.append(
            Issue(
                rel_skill,
                f"frontmatter name {name!r} must be {expected_name!r}",
            )
        )
    if not meta.get("description"):
        issues.append(Issue(rel_skill, "frontmatter needs description"))
    body = FRONTMATTER.sub("", text, count=1)
    for label in LEARNED_BULLETS:
        value = _bullet_value(body, label)
        if value is None:
            issues.append(Issue(rel_skill, f"missing bullet '{label}:'"))
        elif not value or value.startswith("<"):
            issues.append(
                Issue(rel_skill, f"'{label}' is empty or still a placeholder")
            )
    issues.extend(check_evidence(root, evidence_path, expected_name))
    return issues


def check_evidence(root: Path, path: Path, expected_skill: str) -> list[Issue]:
    rel = _rel(root, path)
    if not path.is_file():
        return [Issue(rel, "evidence.json is missing")]
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        return [Issue(rel, f"is not JSON: {exc}", getattr(exc, "lineno", None))]
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue(rel, "must be a JSON object")]
    if data.get("schema_version") != 1:
        issues.append(Issue(rel, "schema_version must be 1"))
    if data.get("skill") != expected_skill:
        issues.append(
            Issue(
                rel,
                f"skill must be {expected_skill!r} (got {data.get('skill')!r})",
            )
        )
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples:
        issues.append(Issue(rel, "examples must be a non-empty list"))
        return issues
    for index, example in enumerate(examples):
        where = f"examples[{index}]"
        if not isinstance(example, dict):
            issues.append(Issue(rel, f"{where} must be an object"))
            continue
        missing = [key for key in EXAMPLE_KEYS if key not in example]
        if missing:
            issues.append(Issue(rel, f"{where} lacks {missing}"))
            continue
        if example["confirmation"] not in CONFIRMATIONS:
            issues.append(
                Issue(
                    rel,
                    f"{where}.confirmation must be {' or '.join(CONFIRMATIONS)}",
                )
            )
        if not isinstance(example["frames"], list) or not example["frames"]:
            issues.append(Issue(rel, f"{where}.frames must be a non-empty list of paths"))
        elif not all(isinstance(frame, str) and frame.strip() for frame in example["frames"]):
            issues.append(Issue(rel, f"{where}.frames entries must be non-empty strings"))
        action = example["executed_action"]
        if not isinstance(action, dict) or not action.get("tool"):
            issues.append(
                Issue(rel, f"{where}.executed_action must be an object with tool")
            )
        elif "arguments" not in action or not isinstance(action["arguments"], dict):
            issues.append(
                Issue(rel, f"{where}.executed_action.arguments must be an object")
            )
        for field in ("task", "episode_or_date", "pose_recipe", "point_reacquisition", "observed_effect"):
            value = example.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(Issue(rel, f"{where}.{field} must be a non-empty string"))
    return issues


def check_memory(memory_dir: Path) -> list[Issue]:
    """Return every format problem in `memory_dir`. Empty means the tree is valid."""
    root = memory_dir
    issues: list[Issue] = []
    if not root.exists():
        return [Issue(str(root), "directory does not exist")]
    if not root.is_dir():
        return [Issue(str(root), "is not a directory")]

    tips = root / "TIPS.md"
    if tips.is_file():
        issues.extend(check_tips(root, tips))
    elif (root / "skills").is_dir():
        # Tips may be absent at the start of a task; they are required once
        # anything has been distilled, because distillation starts from a tip.
        issues.append(
            Issue("TIPS.md", "missing; record tips before distilling learned skills")
        )

    index_path = root / "INDEX.md"
    listed: dict[str, tuple[str, str, int]] = {}
    skills_root = root / "skills"
    on_disk = sorted(
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ) if skills_root.is_dir() else []

    if index_path.is_file():
        index_issues, listed = check_index(root, index_path)
        issues.extend(index_issues)
    elif on_disk:
        issues.append(Issue("INDEX.md", "missing; every learned skill needs a row"))

    for slug in on_disk:
        issues.extend(check_learned_skill(root, skills_root / slug))
        if slug not in listed and index_path.is_file():
            issues.append(
                Issue(
                    "INDEX.md",
                    f"needs a row linking skills/{slug}/SKILL.md",
                )
            )
        elif slug in listed:
            confirmation, _last, line = listed[slug]
            evidence_path = skills_root / slug / "evidence.json"
            if evidence_path.is_file() and confirmation in CONFIRMATIONS:
                try:
                    data = json.loads(evidence_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    data = {}
                examples = data.get("examples") if isinstance(data, dict) else None
                if isinstance(examples, list) and examples:
                    evidence_levels = [
                        ex.get("confirmation")
                        for ex in examples
                        if isinstance(ex, dict)
                    ]
                    if confirmation == "task-confirmed" and "task-confirmed" not in evidence_levels:
                        issues.append(
                            Issue(
                                "INDEX.md",
                                f"{slug} is task-confirmed but evidence.json has no task-confirmed example",
                                line,
                            )
                        )

    for slug, (_confirmation, _last, line) in listed.items():
        if slug not in on_disk:
            issues.append(
                Issue(
                    "INDEX.md",
                    f"links skills/{slug}/SKILL.md, which does not exist",
                    line,
                )
            )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "memory_dir",
        help="path to the session memory/ directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print issues as JSON",
    )
    args = parser.parse_args(argv)
    issues = check_memory(Path(args.memory_dir))
    if args.json:
        print(json.dumps([asdict(issue) for issue in issues], indent=2))
    else:
        for issue in issues:
            print(issue.render())
        checked = Path(args.memory_dir)
        n_skills = 0
        skills_root = checked / "skills"
        if skills_root.is_dir():
            n_skills = sum(1 for path in skills_root.iterdir() if path.is_dir())
        if issues:
            print(f"{n_skills} learned skill(s) checked: {len(issues)} problem(s)")
        else:
            print(f"{n_skills} learned skill(s) checked: OK")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
