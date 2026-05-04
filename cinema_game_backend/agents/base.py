"""
Agentic loop base: runs Claude with tool use until it reaches a final answer.
Handles both custom TMDb tools and Claude's built-in web_search tool.

TODO: Abstract the LLM provider behind a testable interface (e.g. langchain)
so we can substitute other providers or run locally with Ollama.
"""

import json
import anthropic
from langsmith import traceable
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from ..config import MODEL, ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=6)


@traceable(run_type="tool", name="tmdb_search_actor")
async def _tool_search_actor(tmdb: TMDbClient, tool_input: dict) -> str:
    result = await tmdb.search_person(tool_input["name"])
    return json.dumps(
        result.model_dump(mode="json") if result else {"error": "Actor not found"}
    )


@traceable(run_type="tool", name="tmdb_search_movie")
async def _tool_search_movie(tmdb: TMDbClient, tool_input: dict) -> str:
    result = await tmdb.search_movie(
        tool_input["title"],
        year=tool_input.get("year"),
    )
    return json.dumps(
        result.model_dump(mode="json") if result else {"error": "Movie not found"}
    )


@traceable(run_type="tool", name="tmdb_get_movie_cast")
async def _tool_get_movie_cast(tmdb: TMDbClient, tool_input: dict) -> str:
    result = await tmdb.get_movie_cast(tool_input["movie_id"])
    return json.dumps([c.model_dump(mode="json") for c in result])


@traceable(run_type="llm", name="claude_call")
def _call_llm_once(messages: list, system: str) -> anthropic.types.Message:
    """Single traced LLM call without tools — for structured one-shot prompts.

    Swap for provider.invoke_json(prompt, schema) when reusable-llm-provider
    is integrated: the call site in validation_agent._validate_fast_path becomes
    a one-line change.
    """
    return client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        messages=messages,
    )


async def execute_tool(tmdb: TMDbClient, name: str, tool_input: dict) -> str:
    """Dispatch a tool call to the appropriate TMDb handler."""
    if name == "search_actor":
        return await _tool_search_actor(tmdb, tool_input)
    if name == "search_movie":
        return await _tool_search_movie(tmdb, tool_input)
    if name == "get_movie_cast":
        return await _tool_get_movie_cast(tmdb, tool_input)
    return json.dumps({"error": f"Unknown tool: {name}"})


@traceable(run_type="llm", name="claude_call")
def _call_llm(messages: list, system: str, tools: list):
    """Single traced LLM call — appears as an individual span in LangSmith."""
    return client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        tools=tools,
        messages=messages,
    )


@traceable(run_type="chain", name="agentic_loop")
async def run_agent(
    tmdb: TMDbClient,
    system: str,
    user_message: str,
    tools: list,
    max_iterations: int = 10,
) -> str:
    """
    Async agentic loop. Runs Claude with tools until stop_reason == 'end_turn'.
    Returns the final text response from the model.

    web_search is a server-side built-in tool — Anthropic executes it automatically
    and returns the results to Claude; we never need to provide a tool_result for it.
    """
    messages = [{"role": "user", "content": user_message}]

    for iteration in range(max_iterations):
        response = _call_llm(messages, system, tools)

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text_parts = [
                block.text for block in response.content if block.type == "text"
            ]
            return "\n\n".join(text_parts)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                # web_search is executed server-side — skip client dispatch
                if block.name == "web_search":
                    continue
                result = await execute_tool(tmdb, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            # If only web_search was called, Claude handles it internally —
            # loop continues and the next response will include Claude's follow-up.

    return ""
