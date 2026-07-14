"""Tests for validate_move using a mocked TMDbClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from art_graph.cinema_data_providers.tmdb_models import Movie, CastMember
from cinema_game_backend.agents.validation_agent import validate_move


def make_movie(
    title="Thor", movie_id=10195, release_date="2011-04-21", poster_path="/thor.jpg"
):
    return Movie(
        id=movie_id, title=title, release_date=release_date, poster_path=poster_path
    )


def make_cast(*names):
    return [CastMember(id=i + 1, name=n) for i, n in enumerate(names)]


@pytest.fixture
def thor_cast():
    return make_cast(
        "Chris Hemsworth",
        "Natalie Portman",
        "Tom Hiddleston",
        "Anthony Hopkins",
        "Kat Dennings",
        "Stellan Skarsgård",
        "Idris Elba",
        "Rene Russo",
    )


@pytest.fixture
def mock_tmdb(thor_cast):
    tmdb = AsyncMock()
    tmdb.search_movies.return_value = [make_movie()]
    tmdb.get_movie_cast.return_value = thor_cast
    return tmdb


class TestValidMove:
    async def test_both_actors_exact(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portman", from_actor_id=1
        )
        assert result.valid is True
        assert result.from_actor_found is True
        assert result.to_actor_found is True
        assert result.movie_id == 10195
        assert result.movie_title == "Thor"

    async def test_minor_typo_accepted(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portmen", from_actor_id=1
        )
        assert result.valid is True
        assert result.to_actor_found is True


class TestInvalidMove:
    async def test_actor_not_in_cast(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Leonardo DiCaprio", from_actor_id=1
        )
        assert result.valid is False
        assert result.from_actor_found is True
        assert result.to_actor_found is False
        assert "Leonardo DiCaprio" in result.explanation

    async def test_neither_actor_in_cast(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Brad Pitt", "Thor", "Leonardo DiCaprio", from_actor_id=999
        )
        assert result.valid is False
        assert result.from_actor_found is False
        assert result.to_actor_found is False

    async def test_movie_not_found(self, mock_tmdb):
        mock_tmdb.search_movies.return_value = []
        result = await validate_move(
            mock_tmdb,
            "Chris Hemsworth",
            "Nonexistent Movie",
            "Natalie Portman",
            from_actor_id=1,
        )
        assert result.valid is False
        assert "not found" in result.explanation.lower()


class TestMisspelledFinalActor:
    """Regression tests for the bug where a misspelled final actor
    validates correctly but the game fails to detect completion."""

    async def test_misspelled_name_still_valid(self, mock_tmdb):
        # "Kat Denings" -> "Kat Dennings" (distance 1)
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings", from_actor_id=1
        )
        assert result.valid is True
        assert result.to_actor_found is True

    async def test_explanation_uses_canonical_name(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings", from_actor_id=1
        )
        assert "Kat Dennings" in result.explanation

    async def test_to_actor_name_is_canonical(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings", from_actor_id=1
        )
        assert result.to_actor_name == "Kat Dennings"

    async def test_from_actor_name_is_canonical(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemswerth", "Thor", "Kat Dennings", from_actor_id=1
        )
        assert result.from_actor_name == "Chris Hemsworth"


class TestLLMFallback:
    """Tests for LLM fallback when fuzzy matching fails (e.g. nicknames)."""

    @pytest.fixture
    def apocalypse_now_tmdb(self):
        tmdb = AsyncMock()
        tmdb.search_movies.return_value = [
            make_movie(
                title="Apocalypse Now",
                movie_id=28,
                release_date="1979-08-15",
                poster_path="/apocalypse.jpg",
            )
        ]
        tmdb.get_movie_cast.return_value = make_cast(
            "Marlon Brando",
            "Martin Sheen",
            "Robert Duvall",
            "Frederic Forrest",
            "Sam Bottoms",
            "Laurence Fishburne",
            "Dennis Hopper",
        )
        return tmdb

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.invoke_json.return_value = {"matched_name": "Laurence Fishburne"}
        return llm

    async def test_nickname_resolved_by_llm(self, apocalypse_now_tmdb, mock_llm):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            from_actor_id=1,
            llm=mock_llm,
        )
        assert result.valid is True
        assert result.to_actor_found is True
        assert result.to_actor_name == "Laurence Fishburne"

    async def test_nickname_fails_without_llm(self, apocalypse_now_tmdb):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            from_actor_id=1,
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_returns_null_match(self, apocalypse_now_tmdb):
        llm = MagicMock()
        llm.invoke_json.return_value = {"matched_name": None}
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            from_actor_id=1,
            llm=llm,
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_exception_degrades_gracefully(self, apocalypse_now_tmdb):
        llm = MagicMock()
        llm.invoke_json.side_effect = RuntimeError("API timeout")
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            from_actor_id=1,
            llm=llm,
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_not_called_when_fuzzy_matches(
        self, apocalypse_now_tmdb, mock_llm
    ):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Laurence Fishburne",
            from_actor_id=1,
            llm=mock_llm,
        )
        assert result.valid is True
        mock_llm.invoke_json.assert_not_called()


class TestMovieMetadata:
    async def test_result_includes_movie_metadata(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portman", from_actor_id=1
        )
        assert result.movie_id == 10195
        assert result.movie_title == "Thor"
        assert result.movie_year == "2011"
        assert result.poster_url is not None


class TestAmbiguousTitle:
    """Regression tests for the bug where an ambiguous title (shared by
    multiple films) resolves against the wrong TMDb search result and a
    valid move is incorrectly rejected."""

    @pytest.fixture
    def ambiguous_tmdb(self):
        tmdb = AsyncMock()
        tmdb.search_movies.return_value = [
            make_movie(title="The Batman", movie_id=414906, release_date="2022-03-01"),
            make_movie(title="Batman", movie_id=268, release_date="1989-06-21"),
        ]
        casts = {
            414906: make_cast("Robert Pattinson", "Zoë Kravitz", "Paul Dano"),
            268: make_cast("Michael Keaton", "Jack Nicholson", "Kim Basinger"),
        }

        async def get_movie_cast(movie_id):
            return casts[movie_id]

        tmdb.get_movie_cast.side_effect = get_movie_cast
        return tmdb

    async def test_uses_second_candidate_when_first_lacks_actor_pair(
        self, ambiguous_tmdb
    ):
        result = await validate_move(
            ambiguous_tmdb,
            "Jack Nicholson",
            "Batman",
            "Michael Keaton",
            from_actor_id=2,
        )
        assert result.valid is True
        assert result.movie_id == 268
        assert result.movie_title == "Batman"
        assert result.movie_year == "1989"

    async def test_short_circuits_when_first_candidate_matches(self):
        tmdb = AsyncMock()
        tmdb.search_movies.return_value = [
            make_movie(title="Batman", movie_id=268, release_date="1989-06-21"),
            make_movie(title="The Batman", movie_id=414906, release_date="2022-03-01"),
        ]
        tmdb.get_movie_cast.return_value = make_cast("Michael Keaton", "Jack Nicholson")

        result = await validate_move(
            tmdb, "Jack Nicholson", "Batman", "Michael Keaton", from_actor_id=2
        )

        assert result.valid is True
        tmdb.get_movie_cast.assert_called_once_with(268)

    async def test_no_candidate_matches_reports_failure_against_top_ranked(
        self, ambiguous_tmdb
    ):
        result = await validate_move(
            ambiguous_tmdb,
            "Jack Nicholson",
            "Batman",
            "Leonardo DiCaprio",
            from_actor_id=2,
        )
        assert result.valid is False
        assert result.movie_id == 414906
        assert "The Batman" in result.explanation

    async def test_respects_max_candidates_cap(self, monkeypatch):
        monkeypatch.setattr(
            "cinema_game_backend.agents.validation_agent.MAX_MOVIE_SEARCH_CANDIDATES",
            2,
        )
        tmdb = AsyncMock()
        tmdb.search_movies.return_value = [
            make_movie(title="Batman", movie_id=1, release_date="2001-01-01"),
            make_movie(title="Batman", movie_id=2, release_date="2002-01-01"),
            make_movie(title="Batman", movie_id=3, release_date="2003-01-01"),
        ]
        casts = {
            1: make_cast("Nobody Relevant"),
            2: make_cast("Nobody Relevant"),
            3: make_cast("Jack Nicholson", "Michael Keaton"),
        }

        async def get_movie_cast(movie_id):
            return casts[movie_id]

        tmdb.get_movie_cast.side_effect = get_movie_cast

        result = await validate_move(
            tmdb, "Jack Nicholson", "Batman", "Michael Keaton", from_actor_id=1
        )

        assert result.valid is False
        assert tmdb.get_movie_cast.call_count == 2


class TestActorIdentityAnchor:
    """Regression tests for the bug where the chain is anchored by actor
    name rather than TMDb id, so a cast member who merely shares a name
    with the anchored actor is silently accepted as a continuation of
    the chain."""

    async def test_homonym_cast_member_is_rejected_when_id_does_not_match(self):
        tmdb = AsyncMock()
        tmdb.search_movies.return_value = [make_movie(title="Bandits", movie_id=500)]
        tmdb.get_movie_cast.return_value = [
            CastMember(id=999, name="Chris Pine"),  # homonym, wrong person
            CastMember(id=42, name="Cate Blanchett"),
        ]

        result = await validate_move(
            tmdb,
            from_actor="Chris Pine",
            movie_title="Bandits",
            to_actor="Cate Blanchett",
            from_actor_id=64,  # the actual anchored person's TMDb id
        )

        assert result.valid is False
        assert result.from_actor_found is False

    async def test_to_actor_id_is_captured_from_cast_member(self, mock_tmdb):
        """The next actor's TMDb id should come straight from the cast
        member validate_move matched, not require a separate lookup."""
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portman", from_actor_id=1
        )

        assert result.valid is True
        assert result.to_actor_id == 2
