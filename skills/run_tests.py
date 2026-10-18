#!/usr/bin/env python3
"""Discover and run tests under skills/.

Skill folders use hyphens, so they are not importable packages. This runner
loads every test_*.py by path.

    python3 skills/run_tests.py
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def load_file(root: Path, path: Path) -> unittest.TestSuite:
    parts = path.relative_to(root).with_suffix("").parts
    name = "rax_" + "_".join(part.replace("-", "_") for part in parts)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def main() -> int:
    root = Path(__file__).resolve().parent
    suite = unittest.TestSuite()
    files = sorted(p for p in root.rglob("test_*.py") if p.is_file())
    if not files:
        print("No test_*.py files found under skills/", file=sys.stderr)
        return 1
    for path in files:
        suite.addTests(load_file(root, path))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"{result.testsRun} test(s), {len(result.failures)} failure(s), {len(result.errors)} error(s)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
