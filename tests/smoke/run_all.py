"""Run all smoke tests from the repository root."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = [
    "test_latex.py",
    "test_rich_latex.py",
    "test_routing.py",
    "test_blockquote.py",
    "test_polling.py",
    "test_logging.py",
    "test_retry.py",
]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    for test in TESTS:
        path = Path(__file__).resolve().parent / test
        print(f"\n=== {test} ===")
        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, env=env)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
