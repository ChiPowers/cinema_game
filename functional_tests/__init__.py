"""Functional tests for cinema_game_backend.

These tests verify that the backend can make real API calls to external services
(Anthropic, TMDb, etc.) and that the agentic loops work correctly.

Functional tests are never run in CI — they require actual API credentials
and external service access. Run them locally with:

    pytest functional_tests/

Requires valid credentials in secrets/.env
"""
