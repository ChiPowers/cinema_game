# Minimum coverage percentage required for tests to pass
COVERAGE_FAIL = 50

# Run the test suite
test:
	poetry run pytest

# Format the code using Black
format:
	poetry run black .

# Lint the code using Ruff
lint:
	poetry run ruff check .

# Run all quality checks: formatting, linting, and tests
check: format lint test

# Run tests with coverage enforcement (terminal output only)
coverage:
	poetry run pytest --cov=cinema_game_backend --cov-report=term --cov-fail-under=$(COVERAGE_FAIL)

# Run tests with coverage and produce an HTML report
coverage-html:
	poetry run pytest --cov=cinema_game_backend --cov-report=html --cov-fail-under=$(COVERAGE_FAIL)
	@echo "HTML coverage report generated at htmlcov/index.html"
