# Package name, read from pyproject.toml so this Makefile is reusable across projects
PACKAGE := $(shell awk -F'"' '/^name = / {print $$2; exit}' pyproject.toml)

# Minimum coverage percentage required for tests to pass
COVERAGE_FAIL = 50

# Run the unit test suite (excludes functional tests)
test:
	poetry run pytest $(PACKAGE)/tests/

# Run functional tests (requires API credentials in secrets/.env)
test-functional:
	poetry run pytest functional_tests/

# Run all tests (unit + functional)
test-all:
	poetry run pytest $(PACKAGE)/tests/ functional_tests/

# Format the code using Ruff. Applies safe lint fixes (import sorting,
# pyupgrade rewrites) before formatting, so `make check` passes afterwards.
format:
	poetry run ruff check --fix .
	poetry run ruff format .

# Verify formatting without rewriting anything (this is what CI runs)
format-check:
	poetry run ruff format --check .

# Lint the code using Ruff (configured in pyproject.toml [tool.ruff])
lint:
	poetry run ruff check .

# Run all quality checks. Does not modify files; run `make format` to fix.
check: format-check lint test

# Run unit tests with coverage enforcement (terminal output only)
# Omit patterns are configured in pyproject.toml [tool.coverage.run].
coverage:
	poetry run coverage run --source=$(PACKAGE) -m pytest $(PACKAGE)/tests/
	poetry run coverage report --fail-under=$(COVERAGE_FAIL)

# Run unit tests with coverage and produce an HTML report
coverage-html:
	poetry run coverage run --source=$(PACKAGE) -m pytest $(PACKAGE)/tests/
	poetry run coverage report --fail-under=$(COVERAGE_FAIL)
	poetry run coverage html
	@echo "HTML coverage report generated at htmlcov/index.html"

# Run all tests (unit + functional) with coverage enforcement
coverage-all:
	poetry run coverage run --source=$(PACKAGE) -m pytest $(PACKAGE)/tests/ functional_tests/
	poetry run coverage report --fail-under=$(COVERAGE_FAIL)

# Run all tests with coverage and produce an HTML report
coverage-all-html:
	poetry run coverage run --source=$(PACKAGE) -m pytest $(PACKAGE)/tests/ functional_tests/
	poetry run coverage report --fail-under=$(COVERAGE_FAIL)
	poetry run coverage html
	@echo "HTML coverage report generated at htmlcov/index.html"

# Verify every optional dependency is isolated behind a single module.
import-boundaries:
	poetry run python scripts/import_boundaries.py .

# Verify imported packages are declared, and declared in the right group.
deps-check:
	poetry run deptry .

# Report unused code. ADVISORY: read the output rather than trusting it.
deadcode:
	poetry run vulture $(PACKAGE) scripts $(wildcard deadcode-whitelist.py)

# Baseline the existing dead code so it stops blocking work while new dead
# code still surfaces. Commit the result. Two traps are handled here: vulture
# exits 3 whenever it finds anything, and it emits a trailing blank line that
# `ruff format --check` rejects.
deadcode-baseline:
	-poetry run vulture --make-whitelist $(PACKAGE) scripts > deadcode-whitelist.py
	poetry run ruff format deadcode-whitelist.py
	@if [ -s deadcode-whitelist.py ]; then \
	    echo "baseline written to deadcode-whitelist.py - review it, then commit it"; \
	else \
	    rm -f deadcode-whitelist.py; \
	    echo "no dead code found; no baseline needed"; \
	fi

.PHONY: test test-functional test-all format format-check lint check \
        coverage coverage-html coverage-all coverage-all-html \
        import-boundaries deps-check deadcode deadcode-baseline
