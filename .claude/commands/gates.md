Run all quality gates for the project:

1. Run `ruff check .` — lint check
2. Run `ruff format --check .` — format check
3. Run `mypy src/` — type checking
4. Run `pytest --tb=short` — test suite

Report each gate's pass/fail status. If any gate fails, identify the specific errors and fix them. Do NOT proceed with committing until all gates pass.
