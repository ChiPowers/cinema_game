from cinema_game_backend.tools.definitions import TMDB_TOOLS, WEB_SEARCH_TOOL, ALL_TOOLS


class TestTmdbTools:
    def test_three_tools_defined(self):
        assert len(TMDB_TOOLS) == 3

    def test_tool_names(self):
        names = {t["name"] for t in TMDB_TOOLS}
        assert names == {"search_actor", "search_movie", "get_movie_cast"}

    def test_all_have_required_fields(self):
        for tool in TMDB_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_required_params_exist_in_properties(self):
        for tool in TMDB_TOOLS:
            schema = tool["input_schema"]
            for req in schema["required"]:
                assert (
                    req in schema["properties"]
                ), f"{tool['name']} requires '{req}' but it's not in properties"


class TestWebSearchTool:
    def test_has_name_and_type(self):
        assert WEB_SEARCH_TOOL["name"] == "web_search"
        assert "type" in WEB_SEARCH_TOOL


class TestAllTools:
    def test_includes_tmdb_and_web_search(self):
        names = {t["name"] for t in ALL_TOOLS}
        assert "search_actor" in names
        assert "search_movie" in names
        assert "get_movie_cast" in names
        assert "web_search" in names

    def test_length(self):
        assert len(ALL_TOOLS) == len(TMDB_TOOLS) + 1
