"""
Agentic loop base: runs Claude with tool use until it reaches a final answer.
Handles both custom TMDb tools and Claude's built-in web_search tool.

TODO: Abstract the LLM provider behind a testable interface (e.g. langchain)
so we can substitute other providers or run locally with Ollama.
"""

import json
import anthropic
from tools.tmdb import tmdb
from config import MODEL, ANTHROPIC_API_KEY


client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def execute_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool call to the appropriate TMDb handler."""
    if name == "search_actor":
        result = await tmdb.search_person(tool_input["name"])
        return json.dumps(result or {"error": "Actor not found"})

    if name == "search_movie":
        result = await tmdb.search_movie(
            tool_input["title"],
            year=tool_input.get("year"),
        )
        return json.dumps(result or {"error": "Movie not found"})

    if name == "get_movie_cast":
        result = await tmdb.get_movie_cast(tool_input["movie_id"])
        return json.dumps(result)

    return json.dumps({"error": f"Unknown tool: {name}"})


async def run_agent(system: str, user_message: str, tools: list, max_iterations: int = 10) -> str:
    """
    Async agentic loop. Runs Claude with tools until stop_reason == 'end_turn'.
    Returns the final text response from the model.

    web_search is a server-side built-in tool — Anthropic executes it automatically
    and returns the results to Claude; we never need to provide a tool_result for it.
    """
    messages = [{"role": "user", "content": user_message}]

    for _ in range(max_iterations):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                # web_search is executed server-side — skip client dispatch
                if block.name == "web_search":
                    continue
                result = await execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            # If only web_search was called, Claude handles it internally —
            # loop continues and the next response will include Claude's follow-up.

    return ""
