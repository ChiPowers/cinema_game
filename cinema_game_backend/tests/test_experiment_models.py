"""Tests for recorded game session models."""

import pytest

from cinema_game_backend.models.experiment import (
    ExpectedFailure,
    ExpectedSuccess,
    RecordedGame,
    RecordedMove,
)


@pytest.fixture
def valid_move():
    return RecordedMove(
        movie="12 Years a Slave",
        actor="Michael Fassbender",
        expected=ExpectedSuccess(
            movie_id=76203,
            movie_title="12 Years a Slave",
            actor_id=17288,
            actor_name="Michael Fassbender",
        ),
    )


@pytest.fixture
def invalid_move():
    return RecordedMove(
        movie="Batman",
        actor="Jack Nicholson",
        expected=ExpectedFailure(),
    )


@pytest.fixture
def misspelled_move():
    return RecordedMove(
        movie="Thor",
        actor="Kat Denings",
        expected=ExpectedSuccess(
            movie_id=10195,
            movie_title="Thor",
            actor_id=55085,
            actor_name="Kat Dennings",
        ),
    )


@pytest.fixture
def complete_game(valid_move, misspelled_move):
    return RecordedGame(
        start_actor="Brad Pitt",
        end_actor="Kat Dennings",
        moves=[valid_move, misspelled_move],
    )


@pytest.fixture
def game_with_failure(valid_move, invalid_move):
    return RecordedGame(
        start_actor="Brad Pitt",
        end_actor="Jack Nicholson",
        moves=[valid_move, invalid_move],
    )


class TestExpectedOutcomes:
    def test_success_valid_is_true(self):
        s = ExpectedSuccess(movie_id=1, movie_title="T", actor_id=1, actor_name="A")
        assert s.valid is True

    def test_failure_valid_is_false(self):
        f = ExpectedFailure()
        assert f.valid is False


class TestRecordedMove:
    def test_valid_move_fields(self, valid_move):
        assert valid_move.movie == "12 Years a Slave"
        assert valid_move.actor == "Michael Fassbender"
        assert valid_move.expected.valid is True
        assert valid_move.expected.movie_id == 76203

    def test_invalid_move_fields(self, invalid_move):
        assert invalid_move.movie == "Batman"
        assert invalid_move.actor == "Jack Nicholson"
        assert invalid_move.expected.valid is False

    def test_misspelled_actor_records_raw_input(self, misspelled_move):
        assert misspelled_move.actor == "Kat Denings"
        assert misspelled_move.expected.actor_name == "Kat Dennings"


class TestRecordedGame:
    def test_game_structure(self, complete_game):
        assert complete_game.start_actor == "Brad Pitt"
        assert complete_game.end_actor == "Kat Dennings"
        assert len(complete_game.moves) == 2

    def test_game_with_failed_move(self, game_with_failure):
        assert game_with_failure.moves[0].expected.valid is True
        assert game_with_failure.moves[1].expected.valid is False


class TestSerialization:
    def test_round_trip_json(self, complete_game):
        data = complete_game.model_dump()
        restored = RecordedGame(**data)
        assert restored == complete_game

    def test_json_string_round_trip(self, complete_game):
        json_str = complete_game.model_dump_json()
        restored = RecordedGame.model_validate_json(json_str)
        assert restored == complete_game

    def test_load_from_dict(self):
        raw = {
            "start_actor": "A",
            "end_actor": "B",
            "moves": [
                {
                    "movie": "M",
                    "actor": "C",
                    "expected": {"valid": False},
                },
            ],
        }
        game = RecordedGame(**raw)
        assert len(game.moves) == 1
        assert game.moves[0].expected.valid is False

    def test_load_success_from_dict(self):
        raw = {
            "start_actor": "A",
            "end_actor": "B",
            "moves": [
                {
                    "movie": "M",
                    "actor": "C",
                    "expected": {
                        "valid": True,
                        "movie_id": 1,
                        "movie_title": "M",
                        "actor_id": 2,
                        "actor_name": "C",
                    },
                },
            ],
        }
        game = RecordedGame(**raw)
        assert game.moves[0].expected.valid is True
        assert game.moves[0].expected.movie_id == 1
