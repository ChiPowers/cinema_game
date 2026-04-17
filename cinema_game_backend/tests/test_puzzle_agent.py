import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cinema_game_backend.models.tmdb import TmdbPerson, TmdbMovie, TmdbCastMember
from cinema_game_backend.agents.puzzle_agent import (
    _has_short_path,
    _pick_popular_actor,
    _random_walk,
    generate_puzzle,
)


def make_person(id=1, name="Test", popularity=10.0, profile_url=None):
    return TmdbPerson(
        id=id, name=name, popularity=popularity, profile_url=profile_url
    )


def make_movie(id=1, title="Movie", year="2020", popularity=10.0):
    return TmdbMovie(id=id, title=title, year=year, popularity=popularity)


def make_cast(id=1, name="Actor", character="Role", order=0, profile_url=None):
    return TmdbCastMember(
        id=id, name=name, character=character, order=order, profile_url=profile_url
    )


# --- _has_short_path ---


class TestHasShortPath:
    async def test_shared_movie_is_one_hop(self):
        shared = make_movie(id=100)
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(
                side_effect=lambda pid, limit=15: {
                    1: [shared, make_movie(id=101)],
                    2: [shared, make_movie(id=102)],
                }[pid]
            )
            assert await _has_short_path(1, 2, max_hops=1) is True

    async def test_no_shared_movie_no_shortcut(self):
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(
                side_effect=lambda pid, limit=15: {
                    1: [make_movie(id=101)],
                    2: [make_movie(id=102)],
                }[pid]
            )
            mock_tmdb.get_movie_cast = AsyncMock(return_value=[])
            assert await _has_short_path(1, 2, max_hops=2) is False

    async def test_max_hops_zero_skips_two_hop_check(self):
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(
                side_effect=lambda pid, limit=15: {
                    1: [make_movie(id=101)],
                    2: [make_movie(id=102)],
                }[pid]
            )
            assert await _has_short_path(1, 2, max_hops=0) is False

    async def test_two_hop_via_shared_costar(self):
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(
                side_effect=lambda pid, limit=15: {
                    1: [make_movie(id=101)],
                    2: [make_movie(id=102)],
                }[pid]
            )
            costar = make_cast(id=99, name="Costar")
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {
                    101: [costar],
                    102: [costar],
                }[mid]
            )
            assert await _has_short_path(1, 2, max_hops=2) is True

    async def test_two_hop_excludes_start_and_end_actors(self):
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(
                side_effect=lambda pid, limit=15: {
                    1: [make_movie(id=101)],
                    2: [make_movie(id=102)],
                }[pid]
            )
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {
                    101: [make_cast(id=1, name="Start")],
                    102: [make_cast(id=2, name="End")],
                }[mid]
            )
            assert await _has_short_path(1, 2, max_hops=2) is False


# --- _pick_popular_actor ---


class TestPickPopularActor:
    async def test_filters_by_popularity(self):
        people = [
            make_person(id=1, name="Famous", popularity=20.0),
            make_person(id=2, name="Unknown", popularity=1.0),
        ]
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=people)
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 1
                mock_random.choice.side_effect = lambda x: x[0]
                result = await _pick_popular_actor(min_popularity=10.0)

        assert result.id == 1
        assert result.name == "Famous"

    async def test_falls_back_to_all_when_none_eligible(self):
        people = [make_person(id=1, name="Low", popularity=1.0)]
        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=people)
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 1
                mock_random.choice.side_effect = lambda x: x[0]
                result = await _pick_popular_actor(min_popularity=50.0)

        assert result.id == 1


# --- _random_walk ---


class TestRandomWalk:
    async def test_single_hop_produces_three_steps(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        movie = make_movie(id=100, title="The Movie", year="2020", popularity=10.0)
        end_cast = make_cast(id=2, name="End", profile_url="/end.jpg")

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie])
            mock_tmdb.get_movie_cast = AsyncMock(return_value=[end_cast])
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=2, name="End", popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.choice.side_effect = lambda x: x[0]

                path = await _random_walk(start, hops=1, min_popularity=5.0)

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

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[])

            path = await _random_walk(start, hops=1, min_popularity=5.0)

        assert path is None

    async def test_returns_none_when_no_cast(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie])
            mock_tmdb.get_movie_cast = AsyncMock(
                return_value=[make_cast(id=1, name="Start")]
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.choice.side_effect = lambda x: x[0]

                path = await _random_walk(start, hops=1, min_popularity=5.0)

        assert path is None

    async def test_no_repeat_movies_excludes_used(self):
        start = make_person(id=1, name="Start")
        movie1 = make_movie(id=100, title="Movie 1", popularity=10.0)
        movie2 = make_movie(id=101, title="Movie 2", popularity=10.0)
        cast1 = make_cast(id=2, name="Mid")
        cast2 = make_cast(id=3, name="End")

        call_count = 0

        async def mock_get_movies(pid, limit=20):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [movie1, movie2]
            return [movie1, movie2]

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(side_effect=mock_get_movies)
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {
                    100: [cast1],
                    101: [cast2],
                }[mid]
            )
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=3, popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.choice.side_effect = lambda x: x[0]

                path = await _random_walk(
                    start, hops=2, min_popularity=5.0, no_repeat_movies=True
                )

        assert path is not None
        movie_ids = [s["id"] for s in path if s["type"] == "movie"]
        assert len(movie_ids) == len(set(movie_ids))

    async def test_last_hop_prefers_popular_end_actor(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)
        popular = make_cast(id=2, name="Popular")
        unpopular = make_cast(id=3, name="Unpopular")

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie])
            mock_tmdb.get_movie_cast = AsyncMock(
                return_value=[popular, unpopular]
            )
            mock_tmdb.get_person_details = AsyncMock(
                side_effect=lambda pid: {
                    2: make_person(id=2, name="Popular", popularity=20.0),
                    3: make_person(id=3, name="Unpopular", popularity=1.0),
                }[pid]
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.choice.side_effect = lambda x: x[0]

                path = await _random_walk(start, hops=1, min_popularity=10.0)

        assert path is not None
        assert path[-1]["name"] == "Popular"

    async def test_last_hop_falls_back_to_most_popular(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(id=100)
        cast_a = make_cast(id=2, name="Less Unpopular")
        cast_b = make_cast(id=3, name="More Unpopular")

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie])
            mock_tmdb.get_movie_cast = AsyncMock(return_value=[cast_a, cast_b])
            mock_tmdb.get_person_details = AsyncMock(
                side_effect=lambda pid: {
                    2: make_person(id=2, popularity=3.0),
                    3: make_person(id=3, popularity=1.0),
                }[pid]
            )

            path = await _random_walk(start, hops=1, min_popularity=50.0)

        assert path is not None
        assert path[-1]["id"] == 2

    async def test_movie_step_includes_metadata(self):
        start = make_person(id=1, name="Start")
        movie = make_movie(
            id=100, title="Cool Movie", year="2023", popularity=15.0
        )
        movie.poster_url = "/poster.jpg"
        movie.backdrop_url = "/backdrop.jpg"
        end_cast = make_cast(id=2, name="End")

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie])
            mock_tmdb.get_movie_cast = AsyncMock(return_value=[end_cast])
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=2, popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.choice.side_effect = lambda x: x[0]

                path = await _random_walk(start, hops=1, min_popularity=5.0)

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

        async def mock_get_movies(pid, limit=20):
            nonlocal call_count
            call_count += 1
            return [movie1, movie2]

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=[start])
            mock_tmdb.get_person_movies = AsyncMock(side_effect=mock_get_movies)
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid]
            )
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=3, name="End Actor", popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 2
                mock_random.choice.side_effect = lambda x: x[0]
                with patch(
                    "cinema_game_backend.agents.puzzle_agent._has_short_path",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    result = await generate_puzzle("easy")

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

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=[start])
            mock_tmdb.get_person_movies = AsyncMock(return_value=[movie1, movie2])
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid]
            )
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=3, popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 2
                mock_random.choice.side_effect = lambda x: x[0]
                with patch(
                    "cinema_game_backend.agents.puzzle_agent._has_short_path",
                    new_callable=AsyncMock,
                    side_effect=mock_short_path,
                ):
                    result = await generate_puzzle("easy")

        assert result is not None
        assert call_idx == 3

    async def test_raises_after_max_retries(self):
        start = make_person(id=1, name="Start", popularity=10.0)

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=[start])
            mock_tmdb.get_person_movies = AsyncMock(return_value=[])
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 3
                mock_random.choice.side_effect = lambda x: x[0]

                with pytest.raises(RuntimeError, match="Failed to generate"):
                    await generate_puzzle("medium")

    async def test_easy_uses_no_repeat_movies(self):
        start = make_person(id=1, name="Start", popularity=10.0)
        movie1 = make_movie(id=100, popularity=10.0)
        movie2 = make_movie(id=101, popularity=10.0)
        mid_cast = make_cast(id=2, name="Mid")
        end_cast = make_cast(id=3, name="End")

        with patch(
            "cinema_game_backend.agents.puzzle_agent.tmdb"
        ) as mock_tmdb:
            mock_tmdb.get_popular_people = AsyncMock(return_value=[start])
            call_count = 0

            async def mock_get_movies(pid, limit=20):
                nonlocal call_count
                call_count += 1
                return [movie1, movie2]

            mock_tmdb.get_person_movies = AsyncMock(side_effect=mock_get_movies)
            mock_tmdb.get_movie_cast = AsyncMock(
                side_effect=lambda mid: {100: [mid_cast], 101: [end_cast]}[mid]
            )
            mock_tmdb.get_person_details = AsyncMock(
                return_value=make_person(id=3, popularity=10.0)
            )
            with patch("cinema_game_backend.agents.puzzle_agent.random") as mock_random:
                mock_random.randint.return_value = 2
                mock_random.choice.side_effect = lambda x: x[0]
                with patch(
                    "cinema_game_backend.agents.puzzle_agent._has_short_path",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    result = await generate_puzzle("easy")

        movie_ids = [
            s["id"] for s in result["known_solution"] if s["type"] == "movie"
        ]
        assert len(movie_ids) == len(set(movie_ids))
