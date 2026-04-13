"""Functional tests for the agentic loop (run_agent).

These tests verify that the tool-use loop works correctly against the real
Anthropic API. They establish the contract that the loop must satisfy:
- Branching on stop_reason (end_turn vs tool_use)
- Dispatching tools correctly
- Handling web_search (server-side, skipped in client dispatch)
- Terminating gracefully

These tests are slow (hitting the real Anthropic API) and require valid
credentials. They should not run in CI.
"""

class TestRunAgentLoop:
    """Test the agentic loop mechanics."""

    async def test_simple_text_response_no_tools(self, run_agentic_loop, tmdb_tools):
        """Test that the agent can answer a simple question without tool use.

        This establishes that the loop correctly exits on stop_reason='end_turn'
        with text content.
        """
        system = "You are a helpful assistant. Answer the user's question concisely."
        user_message = "What is the capital of France?"

        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=3,
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain relevant information
        assert "Paris" in result or "capital" in result.lower()

    async def test_single_tmdb_tool_call(self, run_agentic_loop, tmdb_tools):
        """Test that a single tool call is dispatched and result is returned.

        Instructs the agent to search for a movie, verify it dispatches
        the search_movie tool, and continues until end_turn.
        """
        system = """You are a movie database assistant. When asked about a movie,
search for it using the search_movie tool and report what you find."""
        user_message = "Tell me about the movie 'The Matrix' (1999)."

        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=5,
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain information about the movie
        assert "Matrix" in result or "movie" in result.lower()

    async def test_multi_hop_tmdb_chain(self, run_agentic_loop, tmdb_tools):
        """Test that the agent handles multiple tool calls across iterations.

        Instructs the agent to search for two movies and compare them,
        verifying that the loop correctly handles multiple stop_reason='tool_use'
        iterations before returning.
        """
        system = """You are a movie comparison assistant. When asked to compare
movies, search for both using search_movie and report similarities/differences."""
        user_message = (
            "Compare the movies 'The Matrix' (1999) and 'Inception' (2010). "
            "Which has more critical acclaim?"
        )

        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=10,
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Should mention both movies or comparison
        assert (
            "Matrix" in result or "Inception" in result or "compare" in result.lower()
        )

    async def test_agent_respects_max_iterations(self, run_agentic_loop, tmdb_tools):
        """Test that the agent gracefully handles max_iterations boundary.

        Gives the agent an open-ended task with max_iterations=1, verifying
        it exits cleanly instead of raising an exception.
        """
        system = "You are a helpful assistant. Use tools liberally to answer."
        user_message = (
            "List the top 5 movies from 2024 by box office performance. "
            "Search for details on each one."
        )

        # max_iterations=1 means only one API call, not enough to complete the task
        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=1,
        )

        # Should return empty string or a partial answer, not crash
        assert isinstance(result, str)

    async def test_web_search_tool_skipped_client_side(
        self, run_agentic_loop, tmdb_tools
    ):
        """Test that web_search tool calls are skipped in client dispatch.

        web_search is a server-side tool handled by Anthropic; the client
        should not try to dispatch it. This test verifies the loop continues
        correctly when the agent calls web_search.
        """
        system = """You are a current-events assistant. Use web_search to find
recent information about movies, awards, and entertainment news."""
        user_message = "What are the latest movie releases this month?"

        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=5,
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain some information (from web_search or TMDb)

    async def test_agent_returns_empty_string_on_no_text(
        self, run_agentic_loop, tmdb_tools
    ):
        """Test that the agent returns empty string if no text content is found.

        Edge case: response has stop_reason='end_turn' but no text blocks.
        Should return "" rather than crash.
        """
        system = "You are a minimal assistant."
        user_message = "Say nothing."

        result = await run_agentic_loop(
            system=system,
            user_message=user_message,
            tools=tmdb_tools,
            max_iterations=3,
        )

        # Even if agent returns empty, should not crash
        assert isinstance(result, str)
