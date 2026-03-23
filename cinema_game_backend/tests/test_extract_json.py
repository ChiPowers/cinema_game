from cinema_game_backend.agents.validation_agent import _extract_json


class TestRawJson:
    def test_clean_json(self):
        result = _extract_json('{"valid": true, "explanation": "Correct!"}')
        assert result == {"valid": True, "explanation": "Correct!"}

    def test_with_whitespace(self):
        result = _extract_json('  {"valid": false}  ')
        assert result == {"valid": False}


class TestMarkdownFenced:
    def test_json_fence(self):
        text = '```json\n{"valid": true, "explanation": "Both actors found."}\n```'
        result = _extract_json(text)
        assert result["valid"] is True

    def test_bare_fence(self):
        text = '```\n{"valid": false, "explanation": "Not found."}\n```'
        result = _extract_json(text)
        assert result["valid"] is False

    def test_nested_backticks(self):
        text = '```json\n{"valid": true}\n```\n'
        result = _extract_json(text)
        assert result == {"valid": True}


class TestEmbeddedInProse:
    def test_json_surrounded_by_text(self):
        text = 'Here is the result: {"valid": true, "explanation": "Found!"} Hope that helps.'
        result = _extract_json(text)
        assert result["valid"] is True

    def test_json_after_prose(self):
        text = 'After checking the database, I found:\n{"valid": false, "explanation": "Actor not in cast."}'
        result = _extract_json(text)
        assert result["valid"] is False


class TestFullValidationShape:
    def test_complete_response(self):
        text = '{"valid": true, "explanation": "Both found.", "movie_id": 76203, "movie_title": "12 Years a Slave", "movie_year": "2013", "poster_url": null, "backdrop_url": null, "from_actor_found": true, "to_actor_found": true}'
        result = _extract_json(text)
        assert result["valid"] is True
        assert result["movie_id"] == 76203
        assert result["poster_url"] is None
        assert result["from_actor_found"] is True


class TestInvalidInput:
    def test_no_json(self):
        assert _extract_json("This is just plain text.") is None

    def test_empty_string(self):
        assert _extract_json("") is None

    def test_malformed_json(self):
        assert _extract_json("{valid: true}") is None

    def test_truncated_json(self):
        assert _extract_json('{"valid": true, "explanation":') is None
