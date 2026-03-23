import pytest
from unittest.mock import AsyncMock, patch
from tools.tmdb import TMDbClient


@pytest.fixture
def client():
    return TMDbClient()


# --- search_person ---


class TestSearchPerson:
    @pytest.mark.asyncio
    async def test_returns_first_result(self, client):
        mock_response = {
            "results": [
                {
                    "id": 287,
                    "name": "Brad Pitt",
                    "popularity": 25.3,
                    "profile_path": "/abc.jpg",
                    "known_for": [
                        {"title": "Fight Club"},
                        {"title": "Troy"},
                    ],
                }
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_person("Brad Pitt")

        assert result.id == 287
        assert result.name == "Brad Pitt"
        assert result.popularity == 25.3
        assert result.profile_url.endswith("/abc.jpg")
        assert "Fight Club" in result.known_for

    @pytest.mark.asyncio
    async def test_returns_none_when_no_results(self, client):
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value={"results": []}
        ):
            result = await client.search_person("Nonexistent Person")

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_profile_path(self, client):
        mock_response = {"results": [{"id": 1, "name": "Test", "known_for": []}]}
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_person("Test")

        assert result.profile_url is None

    @pytest.mark.asyncio
    async def test_known_for_with_tv_shows(self, client):
        mock_response = {
            "results": [
                {
                    "id": 1,
                    "name": "Test",
                    "known_for": [
                        {"title": "A Movie"},
                        {"name": "A TV Show"},  # TV uses "name" not "title"
                    ],
                }
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_person("Test")

        assert result.known_for == ["A Movie", "A TV Show"]


# --- get_person_movies ---


class TestGetPersonMovies:
    @pytest.mark.asyncio
    async def test_returns_sorted_by_popularity(self, client):
        mock_response = {
            "cast": [
                {
                    "id": 1,
                    "title": "Unpopular",
                    "popularity": 2,
                    "release_date": "2020-01-01",
                },
                {
                    "id": 2,
                    "title": "Popular",
                    "popularity": 50,
                    "release_date": "2019-06-15",
                },
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287)

        assert result[0].title == "Popular"
        assert result[1].title == "Unpopular"

    @pytest.mark.asyncio
    async def test_respects_limit(self, client):
        mock_response = {
            "cast": [
                {"id": i, "title": f"Movie {i}", "popularity": i} for i in range(10)
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287, limit=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_extracts_year_from_release_date(self, client):
        mock_response = {
            "cast": [
                {
                    "id": 1,
                    "title": "Test",
                    "popularity": 1,
                    "release_date": "2013-10-18",
                }
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287)

        assert result[0].year == "2013"

    @pytest.mark.asyncio
    async def test_missing_release_date(self, client):
        mock_response = {"cast": [{"id": 1, "title": "Test", "popularity": 1}]}
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287)

        assert result[0].year is None

    @pytest.mark.asyncio
    async def test_empty_release_date(self, client):
        mock_response = {
            "cast": [{"id": 1, "title": "Test", "popularity": 1, "release_date": ""}]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287)

        assert result[0].year is None

    @pytest.mark.asyncio
    async def test_image_urls(self, client):
        mock_response = {
            "cast": [
                {
                    "id": 1,
                    "title": "Test",
                    "popularity": 1,
                    "poster_path": "/poster.jpg",
                    "backdrop_path": "/backdrop.jpg",
                }
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_movies(287)

        assert "w500" in result[0].poster_url
        assert "w1280" in result[0].backdrop_url


# --- search_movie ---


class TestSearchMovie:
    @pytest.mark.asyncio
    async def test_returns_first_result(self, client):
        mock_response = {
            "results": [
                {
                    "id": 76203,
                    "title": "12 Years a Slave",
                    "release_date": "2013-10-18",
                    "poster_path": "/poster.jpg",
                    "backdrop_path": "/backdrop.jpg",
                }
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_movie("12 Years a Slave")

        assert result.id == 76203
        assert result.title == "12 Years a Slave"
        assert result.year == "2013"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_results(self, client):
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value={"results": []}
        ):
            result = await client.search_movie("xyznonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_passes_year_param(self, client):
        mock_get = AsyncMock(
            return_value={
                "results": [{"id": 1, "title": "Test", "release_date": "2013-01-01"}]
            }
        )
        with patch.object(client, "_get", mock_get):
            await client.search_movie("Test", year=2013)

        args, kwargs = mock_get.call_args
        assert kwargs.get("year") == 2013 or args[1].get("year") == 2013


# --- get_movie_cast ---


class TestGetMovieCast:
    @pytest.mark.asyncio
    async def test_returns_cast_list(self, client):
        mock_response = {
            "cast": [
                {
                    "id": 287,
                    "name": "Brad Pitt",
                    "character": "Edwin Epps",
                    "order": 0,
                    "profile_path": "/brad.jpg",
                },
                {
                    "id": 17288,
                    "name": "Michael Fassbender",
                    "character": "Bass",
                    "order": 1,
                },
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_movie_cast(76203)

        assert len(result) == 2
        assert result[0].name == "Brad Pitt"
        assert result[0].character == "Edwin Epps"
        assert result[0].order == 0
        assert result[0].profile_url.endswith("/brad.jpg")
        assert result[1].profile_url is None

    @pytest.mark.asyncio
    async def test_empty_cast(self, client):
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value={"cast": []}
        ):
            result = await client.get_movie_cast(99999)

        assert result == []

    @pytest.mark.asyncio
    async def test_missing_character_defaults(self, client):
        mock_response = {"cast": [{"id": 1, "name": "Test"}]}
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_movie_cast(1)

        assert result[0].character == ""
        assert result[0].order == 999


# --- get_person_details ---


class TestGetPersonDetails:
    @pytest.mark.asyncio
    async def test_returns_details(self, client):
        mock_response = {
            "id": 287,
            "name": "Brad Pitt",
            "popularity": 25.3,
            "profile_path": "/brad.jpg",
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_person_details(287)

        assert result.id == 287
        assert result.name == "Brad Pitt"
        assert result.popularity == 25.3

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, client):
        with patch.object(
            client, "_get", new_callable=AsyncMock, side_effect=Exception("Not found")
        ):
            result = await client.get_person_details(99999)

        assert result is None


# --- get_popular_people ---


class TestGetPopularPeople:
    @pytest.mark.asyncio
    async def test_returns_people_list(self, client):
        mock_response = {
            "results": [
                {
                    "id": 287,
                    "name": "Brad Pitt",
                    "popularity": 25.3,
                    "profile_path": "/brad.jpg",
                    "known_for": [{"title": "Fight Club"}],
                },
                {
                    "id": 1891,
                    "name": "Colin Firth",
                    "popularity": 12.1,
                    "profile_path": None,
                    "known_for": [{"name": "The Crown"}],
                },
            ]
        }
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.get_popular_people(page=1)

        assert len(result) == 2
        assert result[0].name == "Brad Pitt"
        assert result[1].known_for == ["The Crown"]

    @pytest.mark.asyncio
    async def test_empty_results(self, client):
        with patch.object(
            client, "_get", new_callable=AsyncMock, return_value={"results": []}
        ):
            result = await client.get_popular_people()

        assert result == []


# --- _img helper ---


class TestImgHelper:
    def test_with_path(self, client):
        assert client._img("/abc.jpg") == "https://image.tmdb.org/t/p/w500/abc.jpg"

    def test_with_none(self, client):
        assert client._img(None) is None

    def test_with_custom_base(self, client):
        assert (
            client._img("/abc.jpg", "https://example.com")
            == "https://example.com/abc.jpg"
        )
