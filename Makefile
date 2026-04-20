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

# Format the code using Ruff
format:
	poetry run ruff format .

# Lint the code using Ruff (configured in pyproject.toml [tool.ruff])
lint:
	poetry run ruff check .

# Run all quality checks: formatting, linting, and unit tests
check: format lint test

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
