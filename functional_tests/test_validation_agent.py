"""Functional tests for the validation agent (validate_move).

These tests verify that validate_move() correctly verifies movie connections
between actors. They hit the real Anthropic and TMDb APIs.

Test cases establish the contract:
- Valid movie connections are correctly identified
- Invalid connections are rejected
- Typos and misspellings are handled gracefully
- The response schema is correct
"""

import pytest


class TestValidationAgentFunctional:
    """Test the validation agent end-to-end."""

    async def test_valid_movie_connection(self, validate_move_fixture):
        """Test that a known valid connection is correctly identified.

        Brad Pitt and Michael Fassbender both appeared in '12 Years a Slave'.
        """
        result = await validate_move_fixture(
            from_actor="Brad Pitt",
            movie_title="12 Years a Slave",
            to_actor="Michael Fassbender",
        )

        assert result.valid is True
        assert result.explanation is not None
        assert len(result.explanation) > 0
        assert result.movie_id is not None
        assert result.movie_title is not None
        assert isinstance(result.movie_id, int)
        assert isinstance(result.movie_title, str)

    async def test_invalid_movie_connection(self, validate_move_fixture):
        """Test that an invalid connection is correctly rejected.

        Brad Pitt and Keanu Reeves do not share a movie in TMDb
        (searching for 'The Matrixyz', a non-existent movie).
        """
        result = await validate_move_fixture(
            from_actor="Brad Pitt",
            movie_title="The Matrixyz",  # Non-existent movie
            to_actor="Keanu Reeves",
        )

        assert result.valid is False
        assert result.explanation is not None
        assert len(result.explanation) > 0

    async def test_typo_recovery_movie_title(self, validate_move_fixture):
        """Test that minor typos in movie titles are handled gracefully.

        The agent should attempt to find the intended movie via search or
        web_search, not just fail immediately.
        """
        # Misspelled: "The Matirx" instead of "The Matrix"
        result = await validate_move_fixture(
            from_actor="Keanu Reeves",
            movie_title="The Matirx",  # Typo
            to_actor="Laurence Fishburne",
        )

        # Should either find the correct movie or report invalid gracefully
        assert result.valid is not None  # Should have some result
        assert isinstance(result.valid, bool)

    async def test_typo_recovery_actor_name(self, validate_move_fixture):
        """Test that minor typos in actor names are handled gracefully."""
        # Misspelled: "Keanu Reaves" instead of "Keanu Reeves"
        result = await validate_move_fixture(
            from_actor="Keanu Reaves",  # Typo
            movie_title="The Matrix",
            to_actor="Laurence Fishburne",
        )

        # Should either find the correct actor or report invalid
        assert result.valid is not None
        assert isinstance(result.valid, bool)

    async def test_response_schema_valid_move(self, validate_move_fixture):
        """Test that the response schema is correct for a valid move."""
        result = await validate_move_fixture(
            from_actor="Tom Hanks",
            movie_title="Forrest Gump",
            to_actor="Gary Sinise",
        )

        # Check schema
        assert hasattr(result, "valid")
        assert hasattr(result, "explanation")
        assert hasattr(result, "movie_id")
        assert hasattr(result, "movie_title")
        assert hasattr(result, "movie_year")
        assert hasattr(result, "poster_url")
        assert hasattr(result, "backdrop_url")

        # Valid moves should have metadata
        if result.valid:
            assert result.movie_id is not None
            assert result.movie_title is not None

    async def test_response_schema_invalid_move(self, validate_move_fixture):
        """Test that the response schema is correct for an invalid move."""
        result = await validate_move_fixture(
            from_actor="Brad Pitt",
            movie_title="NonexistentMovieXYZ123",
            to_actor="Unknown Actor",
        )

        # Check schema
        assert hasattr(result, "valid")
        assert result.valid is False
        assert hasattr(result, "explanation")
        assert result.explanation is not None
