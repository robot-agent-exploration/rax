#!/usr/bin/env python3
"""Validate a compiled controller against the autonomous-control contract.

    python3 check_controller.py PROJECT
    python3 check_controller.py WORKSPACE
    python3 check_controller.py PROJECT --json

PROJECT is `code/<project>/` (must contain controller.py). WORKSPACE is a
session root that contains `code/<project>/`. The checker reads Python as
syntax only and does not call the robot. It exits 1 when anything breaks
the contract. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

CHECKPOINT_KEYS = (
    "subagent",
    "frames",
    "question",
    "answer",
    "pass_if",
    "on_fail",
)
CHECKPOINT_COLUMNS = (
    "Step",
    "Subagent",
    "Frames",
    "Question",
    "Expected answer",
    "Pass if",
    "On fail",
)
RETURN_KEYS = ("ok", "measured", "why")
CONTEXT_IMPORT = re.compile(
    r"^\s*(?:from\s+api(?:\.runtime)?\s+import\s+.*\bContext\b|import\s+api\.runtime)",
    re.M,
)


@dataclass(frozen=True)
class Issue:
    path: str
    message: str
    line: int | None = None

    def render(self) -> str:
        if self.line is None:
            return f"{self.path}: {self.message}"
        return f"{self.path}:{self.line}: {self.message}"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def parse_tables(text: str) -> list[list[tuple[int, list[str]]]]:
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


def _dict_keys(node: ast.Dict) -> dict[str, ast.expr]:
    keys: dict[str, ast.expr] = {}
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys[key.value] = value
    return keys


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    parts: list[str] = []
    cur: ast.AST = func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


class ControllerVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.issues: list[Issue] = []
        self.has_main = False
        self.checkpoint_count = 0

    def visit_Module(self, node: ast.Module) -> None:
        for child in node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "main":
                self.has_main = True
                args = child.args
                positional = list(args.posonlyargs) + list(args.args)
                if not positional or positional[0].arg != "ctx":
                    self.issues.append(
                        Issue(
                            self.path,
                            "main must take ctx as its first argument",
                            child.lineno,
                        )
                    )
                self._check_main_returns(child)
            if isinstance(child, ast.AsyncFunctionDef) and child.name == "main":
                self.issues.append(
                    Issue(self.path, "main must be a plain function, not async", child.lineno)
                )
        self.generic_visit(node)

    def _check_main_returns(self, node: ast.FunctionDef) -> None:
        returns = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.Return) and child.value is not None
        ]
        if not returns:
            self.issues.append(
                Issue(self.path, "main must return a result dict", node.lineno)
            )
            return
        for ret in returns:
            if isinstance(ret.value, ast.Dict):
                keys = _dict_keys(ret.value)
                missing = [key for key in RETURN_KEYS if key not in keys]
                if missing:
                    self.issues.append(
                        Issue(
                            self.path,
                            f"return dict is missing {missing} (need {', '.join(RETURN_KEYS)})",
                            ret.lineno,
                        )
                    )

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name == "Context" or name.endswith(".Context"):
            self.issues.append(
                Issue(
                    self.path,
                    "do not open Context() here; keep the wrapper outside the project",
                    node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        keys = _dict_keys(node)
        brief = keys.get("checkpoint")
        if isinstance(brief, ast.Dict):
            self._check_checkpoint(brief)
            for key, value in zip(node.keys, node.values):
                if key is not None:
                    self.visit(key)
                if value is not brief:
                    self.visit(value)
            return
        if "subagent" in keys and "question" in keys:
            self._check_checkpoint(node)
            return
        self.generic_visit(node)

    def _check_checkpoint(self, node: ast.Dict) -> None:
        self.checkpoint_count += 1
        keys = _dict_keys(node)
        missing = [key for key in CHECKPOINT_KEYS if key not in keys]
        if missing:
            self.issues.append(
                Issue(
                    self.path,
                    f"checkpoint is missing {missing}",
                    node.lineno,
                )
            )


def check_python(root: Path, path: Path) -> tuple[list[Issue], int]:
    rel = _rel(root, path)
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return [Issue(rel, f"does not compile: {exc.msg}", exc.lineno)], 0
    visitor = ControllerVisitor(rel)
    visitor.visit(tree)
    if path.name == "controller.py" and not visitor.has_main:
        visitor.issues.append(Issue(rel, "must define main(ctx) at module level"))
    if CONTEXT_IMPORT.search(source) and path.name == "controller.py":
        visitor.issues.append(
            Issue(
                rel,
                "do not import Context in the project; the wrapper outside opens it",
            )
        )
    return visitor.issues, visitor.checkpoint_count


def check_readme(root: Path, path: Path, checkpoint_count: int) -> list[Issue]:
    rel = _rel(root, path)
    if not path.is_file():
        return [Issue(rel, "README.md is missing")]
    text = path.read_text(encoding="utf-8", errors="replace")
    issues: list[Issue] = []
    if not re.search(r"controller\.py|main\s*\(\s*ctx\s*\)", text):
        issues.append(
            Issue(rel, "must say how to run controller.py:main(ctx)")
        )
    heading = re.search(r"^#+\s+Perception checkpoints\s*$", text, re.M)
    tables = [
        rows
        for rows in parse_tables(text)
        if rows and rows[0][1][:1] == ["Step"]
    ]
    checkpoint_table = None
    for rows in tables:
        header = rows[0][1]
        if header == list(CHECKPOINT_COLUMNS):
            checkpoint_table = rows
            break
        if header[0] == "Step" and "Subagent" in header:
            issues.append(
                Issue(
                    rel,
                    "Perception checkpoints columns must be "
                    + " | ".join(CHECKPOINT_COLUMNS),
                    rows[0][0],
                )
            )
            checkpoint_table = rows
            break
    if heading is None and checkpoint_table is None:
        if checkpoint_count:
            issues.append(
                Issue(
                    rel,
                    "code returns checkpoints but README has no Perception checkpoints table",
                )
            )
        return issues
    if checkpoint_table is None:
        # Heading present: allow a lone "None" under it.
        after = text[heading.end() :]
        next_heading = re.search(r"^#+\s+", after, re.M)
        body = after[: next_heading.start()] if next_heading else after
        if re.search(r"^\s*None\s*$", body, re.M):
            return issues
        issues.append(
            Issue(
                rel,
                "Perception checkpoints needs the table, or the word None",
                text[: heading.start()].count("\n") + 1,
            )
        )
        return issues
    if checkpoint_table[0][1] != list(CHECKPOINT_COLUMNS):
        return issues
    for line, row in checkpoint_table[1:]:
        if len(row) == 1 and row[0].lower() == "none":
            continue
        if len(row) != len(CHECKPOINT_COLUMNS):
            issues.append(
                Issue(
                    rel,
                    f"checkpoint row has {len(row)} cells, expected {len(CHECKPOINT_COLUMNS)}",
                    line,
                )
            )
            continue
        empties = [
            name
            for name, cell in zip(CHECKPOINT_COLUMNS, row)
            if not cell or cell in {"-", "—", "TODO", "tbd", "TBD"}
        ]
        if empties:
            issues.append(
                Issue(rel, f"checkpoint row is missing {empties}", line)
            )
    return issues


def find_projects(target: Path) -> list[Path]:
    if target.is_file():
        return [target.parent]
    if (target / "controller.py").is_file():
        return [target]
    code = target / "code"
    if code.is_dir():
        projects = sorted(
            path
            for path in code.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        return projects
    return []


def check_project(project: Path, report_root: Path | None = None) -> list[Issue]:
    root = report_root or project
    issues: list[Issue] = []
    controller = project / "controller.py"
    if not controller.is_file():
        return [Issue(_rel(root, controller), "controller.py is missing")]
    if (project / "experiments").exists():
        issues.append(
            Issue(
                _rel(root, project / "experiments"),
                "keep the development wrapper outside code/<project>/",
            )
        )
    py_issues = []
    checkpoints = 0
    for py in sorted(project.rglob("*.py")):
        if py.name.startswith(".") or "__pycache__" in py.parts:
            continue
        found, count = check_python(root, py)
        py_issues.extend(found)
        checkpoints += count
    issues.extend(py_issues)
    issues.extend(check_readme(root, project / "README.md", checkpoints))
    return issues


def check_target(target: Path) -> list[Issue]:
    if not target.exists():
        return [Issue(str(target), "path does not exist")]
    projects = find_projects(target)
    if not projects:
        return [
            Issue(
                str(target),
                "no controller.py here and no code/<project>/ directories",
            )
        ]
    issues: list[Issue] = []
    workspace = (target / "code").is_dir()
    report_root = target if workspace else None
    for project in projects:
        issues.extend(check_project(project, report_root or project))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        help="code/<project>/ directory, or a workspace root that contains code/",
    )
    parser.add_argument("--json", action="store_true", help="print issues as JSON")
    args = parser.parse_args(argv)
    target = Path(args.target)
    issues = check_target(target)
    projects = find_projects(target) if target.exists() else []
    if args.json:
        print(json.dumps([asdict(issue) for issue in issues], indent=2))
    else:
        for issue in issues:
            print(issue.render())
        n = len(projects)
        if issues:
            print(f"{n} project(s) checked: {len(issues)} problem(s)")
        else:
            print(f"{n} project(s) checked: OK")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
