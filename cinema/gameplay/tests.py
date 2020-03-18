import uuid
from datetime import datetime, date
import imdb
import pickle

from .models import Gameplay
from cinema.cinegame.game import GameGraphAndHTTP
from cinema.cinegraph.imdb_grapher import movie_actor_subgraph
from django.test import TestCase
from cinema.tests import data4tests

# Create your tests here.
class GameplayTestCase(TestCase):
    def test_game_data_stored_properly(self):
        
        game_data = {"user":"Test_user", "start_contributor":"Cate Blanchett",
        "end_contributor":"Colin Firth", "start_time":datetime.utcnow(),
        "shortest_path":3}

        # Create the initial game object
        Gameplay.objects.create(**game_data)
        
        # Retrieve the gameplay record  
        gameplay_record = Gameplay.objects.get()
        
        # Check the set and default values are as expected
        self.assertEqual(gameplay_record.user,"Test_user")
        self.assertEqual(gameplay_record.start_contributor, "Cate Blanchett")
        self.assertEqual(gameplay_record.end_contributor, "Colin Firth")
        self.assertEqual(gameplay_record.shortest_path, 3)
        self.assertEqual(gameplay_record.start_time.day, datetime.utcnow().day)
        self.assertEqual(gameplay_record.moves, {})
        self.assertEqual(gameplay_record.is_solved, False)

    def test_store_game_data_GraphandHTTP(self):
        g = data4tests.get_small_graph()

        # load the imdb api
        ia = imdb.IMDb()   

        # play a game to make data that should be stored
        game = GameGraphAndHTTP(949, 147, g, ia)
        # take a step in the game
        game.take_step('Cate Blanchett', 'Julianne Moore', 'The Shipping News')

        # take the next game step
        game.take_step('Julianne Moore', 'Colin Firth', 'A Single Man')
        game_details = Gameplay.objects.all()

        # the details of the game should be updated and marked as complete when the game is solved
        self.assertEqual(game_details.values_list('start_contributor', flat=True)[0], '949')
        self.assertEqual(game_details.values_list('end_contributor', flat=True)[0], '147')
        self.assertEqual(game_details.values_list('shortest_path', flat=True)[0], 3)
        self.assertEqual(game_details.values_list('is_solved', flat=True)[0], True)
        self.assertEqual(game_details.values_list('moves', flat=True)[0],
        {'0': '({949}, {194}, {120824})', '1': '({194}, {147}, {1315981})'})




 
        
        