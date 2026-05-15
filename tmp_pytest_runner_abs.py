from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tmp_pytest_runner_abs.py <pytest_target> <base_name>")

    target = sys.argv[1]
    base_name = sys.argv[2]
    os.chdir(ROOT)
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        exit_code = pytest.main([target, "-q"])

    (ROOT / f"{base_name}.txt").write_text(stdout_buffer.getvalue(), encoding="utf-8")
    (ROOT / f"{base_name}.err").write_text(stderr_buffer.getvalue(), encoding="utf-8")
    (ROOT / f"{base_name}.exit").write_text(str(exit_code), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
