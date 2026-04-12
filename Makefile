# Minimum coverage percentage required for tests to pass
COVERAGE_FAIL = 50

# Run the unit test suite (excludes functional tests)
test:
	poetry run pytest cinema_game_backend/tests/

# Run functional tests (requires API credentials in secrets/.env)
test-functional:
	poetry run pytest functional_tests/

# Run all tests (unit + functional)
test-all:
	poetry run pytest cinema_game_backend/tests/ functional_tests/

# Format the code using Black
format:
	poetry run black .

# Lint the code using Ruff
lint:
	poetry run ruff check .

# Run all quality checks: formatting, linting, and unit tests
check: format lint test

# Run unit tests with coverage enforcement (terminal output only)
coverage:
	poetry run pytest cinema_game_backend/tests/ --cov=cinema_game_backend --cov-report=term --cov-fail-under=$(COVERAGE_FAIL)

# Run unit tests with coverage and produce an HTML report
coverage-html:
	poetry run pytest cinema_game_backend/tests/ --cov=cinema_game_backend --cov-report=html --cov-fail-under=$(COVERAGE_FAIL)
	@echo "HTML coverage report generated at htmlcov/index.html"

# Run all tests (unit + functional) with coverage enforcement
coverage-all:
	poetry run pytest cinema_game_backend/tests/ functional_tests/ --cov=cinema_game_backend --cov-report=term --cov-fail-under=$(COVERAGE_FAIL)

# Run all tests with coverage and produce an HTML report
coverage-all-html:
	poetry run pytest cinema_game_backend/tests/ functional_tests/ --cov=cinema_game_backend --cov-report=html --cov-fail-under=$(COVERAGE_FAIL)
	@echo "HTML coverage report generated at htmlcov/index.html"
