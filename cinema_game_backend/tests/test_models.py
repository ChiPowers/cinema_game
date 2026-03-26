import pytest
from pydantic import ValidationError
from cinema_game_backend.models.game import (
    Actor,
    MovieStep,
    ActorStep,
    Move,
    GameState,
    NewGameResponse,
    MoveRequest,
    MoveResponse,
)

# --- Actor ---


class TestActor:
    def test_basic(self):
        a = Actor(name="Brad Pitt", id=287)
        assert a.name == "Brad Pitt"
        assert a.id == 287
        assert a.profile_url is None

    def test_with_profile_url(self):
        a = Actor(
            name="Brad Pitt",
            id=287,
            profile_url="https://image.tmdb.org/t/p/w500/abc.jpg",
        )
        assert a.profile_url == "https://image.tmdb.org/t/p/w500/abc.jpg"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            Actor(name="Brad Pitt")

    def test_wrong_id_type(self):
        with pytest.raises(ValidationError):
            Actor(name="Brad Pitt", id="not_an_int")

    def test_round_trip(self):
        a = Actor(name="Brad Pitt", id=287, profile_url="https://example.com/img.jpg")
        d = a.model_dump()
        assert Actor(**d) == a


# --- MovieStep ---


class TestMovieStep:
    def test_basic(self):
        m = MovieStep(type="movie", title="12 Years a Slave", id=76203)
        assert m.type == "movie"
        assert m.title == "12 Years a Slave"
        assert m.year is None
        assert m.poster_url is None
        assert m.backdrop_url is None

    def test_with_all_fields(self):
        m = MovieStep(
            type="movie",
            title="12 Years a Slave",
            id=76203,
            year="2013",
            poster_url="https://image.tmdb.org/t/p/w500/poster.jpg",
            backdrop_url="https://image.tmdb.org/t/p/w1280/backdrop.jpg",
        )
        assert m.year == "2013"
        assert m.poster_url is not None

    def test_wrong_type_literal(self):
        with pytest.raises(ValidationError):
            MovieStep(type="actor", title="12 Years a Slave", id=76203)

    def test_round_trip(self):
        m = MovieStep(type="movie", title="12 Years a Slave", id=76203, year="2013")
        assert MovieStep(**m.model_dump()) == m


# --- ActorStep ---


class TestActorStep:
    def test_basic(self):
        a = ActorStep(type="actor", name="Michael Fassbender", id=17288)
        assert a.type == "actor"
        assert a.profile_url is None

    def test_wrong_type_literal(self):
        with pytest.raises(ValidationError):
            ActorStep(type="movie", name="Michael Fassbender", id=17288)

    def test_round_trip(self):
        a = ActorStep(type="actor", name="Michael Fassbender", id=17288)
        assert ActorStep(**a.model_dump()) == a


# --- Move ---


class TestMove:
    def test_minimal(self):
        m = Move(
            from_actor="Brad Pitt",
            movie="12 Years a Slave",
            to_actor="Michael Fassbender",
        )
        assert m.movie_id is None
        assert m.movie_title is None
        assert m.movie_year is None
        assert m.poster_url is None
        assert m.backdrop_url is None

    def test_with_tmdb_metadata(self):
        m = Move(
            from_actor="Brad Pitt",
            movie="12 Years a Slave",
            to_actor="Michael Fassbender",
            movie_id=76203,
            movie_title="12 Years a Slave",
            movie_year="2013",
            poster_url="https://image.tmdb.org/t/p/w500/poster.jpg",
            backdrop_url="https://image.tmdb.org/t/p/w1280/backdrop.jpg",
        )
        assert m.movie_id == 76203

    def test_round_trip(self):
        m = Move(
            from_actor="A",
            movie="B",
            to_actor="C",
            movie_id=1,
            movie_title="B",
            movie_year="2020",
        )
        assert Move(**m.model_dump()) == m


# --- MoveRequest ---


class TestMoveRequest:
    def test_basic(self):
        r = MoveRequest(movie="The Dark Knight", next_actor="Heath Ledger")
        assert r.movie == "The Dark Knight"
        assert r.next_actor == "Heath Ledger"

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            MoveRequest(movie="The Dark Knight")


# --- MoveResponse ---


class TestMoveResponse:
    def test_valid_move(self):
        r = MoveResponse(
            valid=True,
            explanation="Correct!",
            movie_id=155,
            movie_title="The Dark Knight",
            movie_year="2008",
            game_status="in_progress",
            current_actor=Actor(name="Heath Ledger", id=1810),
        )
        assert r.valid is True
        assert r.game_status == "in_progress"

    def test_invalid_move(self):
        r = MoveResponse(
            valid=False,
            explanation="Actor not found in cast.",
            game_status="in_progress",
            current_actor=Actor(name="Brad Pitt", id=287),
        )
        assert r.valid is False
        assert r.movie_id is None

    def test_won_status(self):
        r = MoveResponse(
            valid=True,
            explanation="Correct!",
            game_status="won",
            current_actor=Actor(name="Colin Firth", id=1891),
        )
        assert r.game_status == "won"

    def test_invalid_game_status(self):
        with pytest.raises(ValidationError):
            MoveResponse(
                valid=True,
                explanation="Correct!",
                game_status="abandoned",
                current_actor=Actor(name="Brad Pitt", id=287),
            )


# --- NewGameResponse ---


class TestNewGameResponse:
    def test_basic(self):
        r = NewGameResponse(
            game_id="abc-123",
            start_actor=Actor(name="Brad Pitt", id=287),
            end_actor=Actor(name="Colin Firth", id=1891),
            difficulty="medium",
            min_moves=3,
        )
        assert r.game_id == "abc-123"
        assert r.start_actor.name == "Brad Pitt"
        assert r.min_moves == 3


# --- GameState ---


class TestGameState:
    def test_empty_game(self):
        g = GameState(
            id="abc-123",
            start_actor=Actor(name="Brad Pitt", id=287),
            end_actor=Actor(name="Colin Firth", id=1891),
            difficulty="medium",
            min_moves=3,
            current_actor=Actor(name="Brad Pitt", id=287),
            moves=[],
            status="in_progress",
        )
        assert g.moves == []
        assert g.status == "in_progress"
        assert g.created_at is None

    def test_with_moves(self):
        move = Move(
            from_actor="Brad Pitt",
            movie="12 Years a Slave",
            to_actor="Michael Fassbender",
        )
        g = GameState(
            id="abc-123",
            start_actor=Actor(name="Brad Pitt", id=287),
            end_actor=Actor(name="Colin Firth", id=1891),
            difficulty="medium",
            min_moves=3,
            current_actor=Actor(name="Michael Fassbender", id=17288),
            moves=[move],
            status="in_progress",
        )
        assert len(g.moves) == 1
        assert g.current_actor.name == "Michael Fassbender"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            GameState(
                id="abc-123",
                start_actor=Actor(name="Brad Pitt", id=287),
                end_actor=Actor(name="Colin Firth", id=1891),
                difficulty="medium",
                min_moves=3,
                current_actor=Actor(name="Brad Pitt", id=287),
                moves=[],
                status="abandoned",
            )

    def test_round_trip(self):
        move = Move(
            from_actor="Brad Pitt",
            movie="12 Years a Slave",
            to_actor="Michael Fassbender",
        )
        g = GameState(
            id="abc-123",
            start_actor=Actor(name="Brad Pitt", id=287),
            end_actor=Actor(name="Colin Firth", id=1891),
            difficulty="medium",
            min_moves=3,
            current_actor=Actor(name="Michael Fassbender", id=17288),
            moves=[move],
            status="in_progress",
            created_at="2026-03-17T00:00:00",
        )
        assert GameState(**g.model_dump()) == g
