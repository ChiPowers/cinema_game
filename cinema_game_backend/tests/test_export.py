"""Tests for database-to-RecordedGame export."""

import pytest
from unittest.mock import patch
from cinema_game_backend.experiments.export import list_game_ids, export_game
from cinema_game_backend.models.experiment import RecordedGame, ExpectedSuccess


@pytest.fixture
def sample_game_dict():
    return {
        "id": "abc-123",
        "start_actor": {"name": "Brad Pitt", "id": 287},
        "end_actor": {"name": "Colin Firth", "id": 1372},
        "difficulty": "medium",
        "known_solution": [],
        "moves": [
            {
                "from_actor": "Brad Pitt",
                "movie": "12 Years a Slave",
                "to_actor": "Michael Fassbender",
                "movie_id": 76203,
                "movie_title": "12 Years a Slave",
                "movie_year": "2013",
                "poster_url": None,
                "backdrop_url": None,
                "from_actor_id": 287,
                "to_actor_id": 17288,
            },
            {
                "from_actor": "Michael Fassbender",
                "movie": "X-Men: Apocalypse",
                "to_actor": "Nicholas Hoult",
                "movie_id": 246655,
                "movie_title": "X-Men: Apocalypse",
                "movie_year": "2016",
                "poster_url": None,
                "backdrop_url": None,
                "from_actor_id": 17288,
                "to_actor_id": 4586,
            },
        ],
        "current_actor": {"name": "Nicholas Hoult", "id": 4586},
        "status": "in_progress",
        "strikes": 0,
        "created_at": "2025-01-01 00:00:00",
    }


@pytest.fixture
def empty_game_dict():
    return {
        "id": "empty-456",
        "start_actor": {"name": "Tom Hanks", "id": 31},
        "end_actor": {"name": "Meryl Streep", "id": 5064},
        "difficulty": "easy",
        "known_solution": [],
        "moves": [],
        "current_actor": {"name": "Tom Hanks", "id": 31},
        "status": "in_progress",
        "strikes": 0,
        "created_at": "2025-01-01 00:00:00",
    }


class TestListGameIds:
    @patch("cinema_game_backend.experiments.export.list_games")
    def test_empty(self, mock_list):
        mock_list.return_value = []
        assert list_game_ids() == []

    @patch("cinema_game_backend.experiments.export.list_games")
    def test_returns_summary(self, mock_list, sample_game_dict):
        mock_list.return_value = [sample_game_dict]
        result = list_game_ids()

        assert len(result) == 1
        g = result[0]
        assert g["game_id"] == "abc-123"
        assert g["difficulty"] == "medium"
        assert g["start_actor"] == "Brad Pitt"
        assert g["end_actor"] == "Colin Firth"
        assert g["status"] == "in_progress"
        assert g["moves"] == 2
        assert g["created_at"] == "2025-01-01 00:00:00"

    @patch("cinema_game_backend.experiments.export.list_games")
    def test_passes_limit(self, mock_list):
        mock_list.return_value = []
        list_game_ids(limit=5)
        mock_list.assert_called_once_with(limit=5)

    @patch("cinema_game_backend.experiments.export.list_games")
    def test_default_limit_is_none(self, mock_list):
        mock_list.return_value = []
        list_game_ids()
        mock_list.assert_called_once_with(limit=None)


class TestExportGame:
    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_basic(self, mock_load, sample_game_dict):
        mock_load.return_value = sample_game_dict
        game = export_game("abc-123")

        assert isinstance(game, RecordedGame)
        assert game.start_actor == "Brad Pitt"
        assert game.end_actor == "Colin Firth"
        assert len(game.moves) == 2

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_moves_are_expected_success(self, mock_load, sample_game_dict):
        mock_load.return_value = sample_game_dict
        game = export_game("abc-123")

        for move in game.moves:
            assert isinstance(move.expected, ExpectedSuccess)
            assert move.expected.valid is True

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_move_fields(self, mock_load, sample_game_dict):
        mock_load.return_value = sample_game_dict
        game = export_game("abc-123")

        first = game.moves[0]
        assert first.movie == "12 Years a Slave"
        assert first.actor == "Michael Fassbender"
        assert first.expected.movie_id == 76203
        assert first.expected.movie_title == "12 Years a Slave"
        assert first.expected.actor_name == "Michael Fassbender"

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_populates_actor_ids(self, mock_load, sample_game_dict):
        mock_load.return_value = sample_game_dict
        game = export_game("abc-123")

        assert game.start_actor_id == 287
        assert game.moves[0].expected.actor_id == 17288
        assert game.moves[1].expected.actor_id == 4586

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_empty_game(self, mock_load, empty_game_dict):
        mock_load.return_value = empty_game_dict
        game = export_game("empty-456")

        assert game.start_actor == "Tom Hanks"
        assert game.end_actor == "Meryl Streep"
        assert game.moves == []

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_not_found(self, mock_load):
        mock_load.return_value = None
        with pytest.raises(ValueError, match="Game not found"):
            export_game("no-such-game")

    @patch("cinema_game_backend.experiments.export.load_game")
    def test_export_round_trip_json(self, mock_load, sample_game_dict):
        mock_load.return_value = sample_game_dict
        game = export_game("abc-123")

        json_str = game.model_dump_json()
        restored = RecordedGame.model_validate_json(json_str)
        assert restored == game
