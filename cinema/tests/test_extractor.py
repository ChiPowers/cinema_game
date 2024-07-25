from cinema.cinegraph import extractor
from . import data4tests
from cinema.imdb_config import ia

from django.test import TestCase


class TestExtractor(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # def test_bacon(self):
    #     # Kevin Bacon
    #     bacon = data4tests.get_bacon(ia)
    #     self.assertEqual("0000102", bacon.getID())
    #     films = extractor.filmography_filter(bacon, roles="actor")
    #     ids = {film.getID() for film in films}
    #     # Kevin Bacon was an actor in The Air I Breathe
    #     self.assertIn("0485851", ids)

    # def test_sarah(self):
    #     # Sarah Michelle Gellar
    #     sarah = data4tests.get_sarah(ia)
    #     self.assertEqual("0001264", sarah.getID())
    #     films = extractor.filmography_filter(sarah, roles=("actress", "self"))
    #     ids = {film.getID() for film in films}
    #     # Sarah Michelle Gellar was an actress in The Air I Breathe
    #     self.assertIn("0485851", ids)
    #     # She appeared as herself in A Powerful Noise Live
    #     self.assertIn("1392211", ids)

    # TODO: fix currently failing because filmography key is missing

    # def test_natalie(self):
    #     # Natalie Portman
    #     natalie = data4tests.get_natalie(ia)
    #     self.assertEqual("0000204", natalie.getID())
    #     # get works of where Natalie Portman has any job
    #     films = extractor.filmography_filter(natalie)
    #     ids = {film.getID() for film in films}
    #     # Natalie Portman appeared in A Powerful Noise Live
    #     self.assertIn("1392211", ids)

    # def test_work_intersection(self):
    #     # Kevin Bacon and Sarah Michelle Geller were both in The Air I Breathe
    #     bacon = data4tests.get_bacon(ia)
    #     bacon_films = extractor.filmography_filter(bacon, roles="actor")
    #     sarah = data4tests.get_sarah(ia)
    #     sarah_films = extractor.filmography_filter(sarah, roles="actress")
    #     common_works = extractor.work_intersection(bacon_films, sarah_films)
    #     ids = {film.getID() for film in common_works}
    #     self.assertIn("0485851", ids)
