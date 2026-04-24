import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from art_graph.cinema_data_providers.tmdb_models import (
    Person,
    MovieCreditRole,
    CastMember,
)
from cinema_game_backend.agents.puzzle_agent import (
    _has_short_path,
    _pick_popular_actor,
    _random_walk,
    generate_puzzle,
)


def make_person(id=1, name="Test", popularity=10.0, profile_path=None):
    return Person(id=id, name=name, popularity=popularity, profile_path=profile_path)


def make_movie(id=1, title="Movie", release_date=date(2020, 1, 1), popularity=10.0):
    return MovieCreditRole(
        id=id, title=title, release_date=release_date, popularity=popularity
    )


def make_cast(id=1, name="Actor", character="Role", order=0, profile_path=None):
    return CastMember(
        id=id, name=name, character=character, order=order, profile_path=profile_path
    )


def make_tmdb(**methods):
    tmdb = MagicMock()
    for name, impl in methods.items():
        setattr(tmdb, name, AsyncMock(side_effect=impl) if callable(impl) else AsyncMock(return_value=impl))
    return tmdb


# --- _has_short_path ---


class TestHasShortPath:
    async def test_shared_movie_is_one_hop(self):
        shared = make_movie(id=100)
        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=15: {
                1: [shared, make_movie(id=101)],
                2: [shared, make_movie(id=102)],
            }[pid]
        )
        assert await _has_short_path(tmdb, 1, 2, max_hops=1) is True

    async def test_no_shared_movie_no_shortcut(self):
        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=15: {
                1: [make_movie(id=101)],
                2: [make_movie(id=102)],
            }[pid],
            get_movie_cast=lambda mid: [],
        )
        assert await _has_short_path(tmdb, 1, 2, max_hops=2) is False

    async def test_max_hops_zero_skips_two_hop_check(self):
        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=15: {
                1: [make_movie(id=101)],
                2: [make_movie(id=102)],
            }[pid]
        )
        assert await _has_short_path(tmdb, 1, 2, max_hops=0) is False

    async def test_two_hop_via_shared_costar(self):
        costar = make_cast(id=99, name="Costar")
        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=15: {
                1: [make_movie(id=101)],
                2: [make_movie(id=102)],
            }[pid],
            get_movie_cast=lambda mid: {
                101: [costar],
                102: [costar],
            }[mid],
        )
        assert await _has_short_path(tmdb, 1, 2, max_hops=2) is True

    async def test_two_hop_excludes_start_and_end_actors(self):
        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=15: {
                1: [make_movie(id=101)],
                2: [make_movie(id=102)],
            }[pid],
            get_movie_cast=lambda mid: {
                101: [make_cast(id=1, name="Start")],
                102: [make_cast(id=2, name="End")],
            }[mid],
        )
        assert await _has_short_path(tmdb, 1, 2, max_hops=2) is False


# --- _pick_popular_actor ---


class TestPickPopularActor:
    async def test_filters_by_popularity(self):
        people = [
            make_person(id=1, name="Famous", popularity=20.0),
            make_person(id=2, name="Unknown", popularity=1.0),
        ]
        tmdb = make_tmdb(get_popular_people=people)
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 1
            mock_random.choice.side_effect = lambda x: x[0]
            result = await _pick_popular_actor(tmdb, min_popularity=10.0)

        assert result.id == 1
        assert result.name == "Famous"

    async def test_falls_back_to_all_when_none_eligible(self):
        people = [make_person(id=1, name="Low", popularity=1.0)]
        tmdb = make_tmdb(get_popular_people=people)
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 1
            mock_random.choice.side_effect = lambda x: x[0]
            result = await _pick_popular_actor(tmdb, min_popularity=50.0)

        assert result.id == 1


# --- _random_walk ---


class TestRandomWalk:
    async def test_single_hop_produces_three_steps(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        movie = make_movie(
            id=100, title="The Movie", release_date=date(2020, 1, 1), popularity=10.0
        )
        end_cast = make_cast(id=2, name="End", profile_path="/end.jpg")

        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=20: [movie],
            get_movie_cast=lambda mid: [end_cast],
            get_person_details=lambda pid: make_person(id=2, name="End", popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.choice.side_effect = lambda x: x[0]
            path = await _random_walk(tmdb, start, hops=1, min_popularity=5.0)

        assert path is not None
        assert len(path) == 3
        assert path[0]["type"] == "actor"
        assert path[0]["name"] == "Start"
        assert path[1]["type"] == "movie"
        assert path[1]["title"] == "The Movie"
        assert path[2]["type"] == "actor"
        assert path[2]["name"] == "End"

    async def test_returns_none_when_no_movies(self):
        start = make_person(id=1, name="Start")
        tmdb = make_tmdb(get_person_movies=lambda pid, limit=20: [])
        path = await _random_walk(tmdb, start, hops=1, min_popularity=5.0)
        assert path is None

    async def test_returns_none_when_no_cast(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)

        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=20: [movie],
            get_movie_cast=lambda mid: [make_cast(id=1, name="Start")],
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.choice.side_effect = lambda x: x[0]
            path = await _random_walk(tmdb, start, hops=1, min_popularity=5.0)

        assert path is None

    async def test_no_repeat_movies_excludes_used(self):
        start = make_person(id=1, name="Start")
        movie1 = make_movie(id=100, title="Movie 1", popularity=10.0)
        movie2 = make_movie(id=101, title="Movie 2", popularity=10.0)
        cast1 = make_cast(id=2, name="Mid")
        cast2 = make_cast(id=3, name="End")

        call_count = 0

        def mock_get_movies(pid, limit=20):
            nonlocal call_count
            call_count += 1
            return [movie1, movie2]

        tmdb = make_tmdb(
            get_person_movies=mock_get_movies,
            get_movie_cast=lambda mid: {100: [cast1], 101: [cast2]}[mid],
            get_person_details=lambda pid: make_person(id=3, popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.choice.side_effect = lambda x: x[0]
            path = await _random_walk(
                tmdb, start, hops=2, min_popularity=5.0, no_repeat_movies=True
            )

        assert path is not None
        movie_ids = [s["id"] for s in path if s["type"] == "movie"]
        assert len(movie_ids) == len(set(movie_ids))

    async def test_last_hop_prefers_popular_end_actor(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)
        popular = make_cast(id=2, name="Popular")
        unpopular = make_cast(id=3, name="Unpopular")

        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=20: [movie],
            get_movie_cast=lambda mid: [popular, unpopular],
            get_person_details=lambda pid: {
                2: make_person(id=2, name="Popular", popularity=20.0),
                3: make_person(id=3, name="Unpopular", popularity=1.0),
            }[pid],
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.choice.side_effect = lambda x: x[0]
            path = await _random_walk(tmdb, start, hops=1, min_popularity=10.0)

        assert path is not None
        assert path[-1]["name"] == "Popular"

    async def test_last_hop_falls_back_to_most_popular(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)
        cast_a = make_cast(id=2, name="Less Unpopular")
        cast_b = make_cast(id=3, name="More Unpopular")

        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=20: [movie],
            get_movie_cast=lambda mid: [cast_a, cast_b],
            get_person_details=lambda pid: {
                2: make_person(id=2, popularity=3.0),
                3: make_person(id=3, popularity=1.0),
            }[pid],
        )
        path = await _random_walk(tmdb, start, hops=1, min_popularity=50.0)

        assert path is not None
        assert path[-1]["id"] == 2

    async def test_movie_step_includes_metadata(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(
            id=100, title="Cool Movie", release_date=date(2023, 6, 15), popularity=15.0
        )
        end_cast = make_cast(id=2, name="End")

        tmdb = make_tmdb(
            get_person_movies=lambda pid, limit=20: [movie],
            get_movie_cast=lambda mid: [end_cast],
            get_person_details=lambda pid: make_person(id=2, popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.choice.side_effect = lambda x: x[0]
            path = await _random_walk(tmdb, start, hops=1, min_popularity=5.0)

        movie_step = path[1]
        assert movie_step["title"] == "Cool Movie"
        assert movie_step["year"] == "2023"
        assert movie_step["id"] == 100


# --- generate_puzzle ---


class TestGeneratePuzzle:
    async def test_returns_valid_puzzle_structure(self):
        start = make_person(id=1, name="Start Actor", popularity=10.0)
        movie1 = make_movie(id=100, title="Bridge Movie 1", popularity=10.0)
        movie2 = make_movie(id=101, title="Bridge Movie 2", popularity=10.0)
        mid_cast = make_cast(id=2, name="Mid Actor")
        end_cast = make_cast(id=3, name="End Actor")

        call_count = 0

        def mock_get_movies(pid, limit=20):
            nonlocal call_count
            call_count += 1
            return [movie1, movie2]

        tmdb = make_tmdb(
            get_popular_people=[start],
            get_person_movies=mock_get_movies,
            get_movie_cast=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid],
            get_person_details=lambda pid: make_person(id=3, name="End Actor", popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 2
            mock_random.choice.side_effect = lambda x: x[0]
            with patch(
                "cinema_game_backend.agents.puzzle_agent._has_short_path",
                new_callable=AsyncMock,
                return_value=False,
            ):
                result = await generate_puzzle(tmdb, "easy")

        assert "start_actor" in result
        assert "end_actor" in result
        assert "difficulty" in result
        assert "min_moves" in result
        assert "known_solution" in result
        assert result["difficulty"] == "easy"
        assert result["start_actor"]["name"] == "Start Actor"
        assert result["end_actor"]["name"] == "End Actor"

    async def test_retries_on_short_path(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        movie1 = make_movie(id=100, popularity=10.0)
        movie2 = make_movie(id=101, popularity=10.0)
        mid_cast = make_cast(id=2, name="Mid")
        end_cast = make_cast(id=3, name="End")

        short_path_results = [True, True, False]
        call_idx = 0

        async def mock_short_path(*args, **kwargs):
            nonlocal call_idx
            result = short_path_results[call_idx]
            call_idx += 1
            return result

        tmdb = make_tmdb(
            get_popular_people=[start],
            get_person_movies=lambda pid, limit=20: [movie1, movie2],
            get_movie_cast=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid],
            get_person_details=lambda pid: make_person(id=3, popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 2
            mock_random.choice.side_effect = lambda x: x[0]
            with patch(
                "cinema_game_backend.agents.puzzle_agent._has_short_path",
                new_callable=AsyncMock,
                side_effect=mock_short_path,
            ):
                result = await generate_puzzle(tmdb, "easy")

        assert result is not None
        assert call_idx == 3

    async def test_raises_after_max_retries(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        tmdb = make_tmdb(
            get_popular_people=[start],
            get_person_movies=lambda pid, limit=20: [],
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 3
            mock_random.choice.side_effect = lambda x: x[0]

            with pytest.raises(RuntimeError, match="Failed to generate"):
                await generate_puzzle(tmdb, "medium")

    async def test_easy_uses_no_repeat_movies(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        movie1 = make_movie(id=100, popularity=10.0)
        movie2 = make_movie(id=101, popularity=10.0)
        mid_cast = make_cast(id=2, name="Mid")
        end_cast = make_cast(id=3, name="End")

        call_count = 0

        def mock_get_movies(pid, limit=20):
            nonlocal call_count
            call_count += 1
            return [movie1, movie2]

        tmdb = make_tmdb(
            get_popular_people=[start],
            get_person_movies=mock_get_movies,
            get_movie_cast=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid],
            get_person_details=lambda pid: make_person(id=3, popularity=10.0),
        )
        with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
            mock_random.randint.return_value = 2
            mock_random.choice.side_effect = lambda x: x[0]
            with patch(
                "cinema_game_backend.agents.puzzle_agent._has_short_path",
                new_callable=AsyncMock,
                return_value=False,
            ):
                result = await generate_puzzle(tmdb, "easy")

        movie_ids = [s["id"] for s in result["known_solution"] if s["type"] == "movie"]
        assert len(movie_ids) == len(set(movie_ids))
