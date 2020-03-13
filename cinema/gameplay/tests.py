import uuid
from datetime import datetime, date
import imdb
import pickle

from .models import Gameplay
from cinema.cinegame.game import GameGraphAndHTTP
from cinema.cinegraph.imdb_grapher import movie_actor_subgraph
from django.test import TestCase

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
        # load the graph TODO: make it efficient.
        with open('professional_graph05.pkl', 'rb') as f:
            g = pickle.load(f)

        g = movie_actor_subgraph(g)

        # load the imdb api
        ia = imdb.IMDb()   

        # play a game to make data that should be stored
        game = GameGraphAndHTTP(949, 147, g, ia)
        print(game.take_step('Cate Blanchett', 'Julianne Moore', 'The Shipping News'))
        

        # the details of the game should be stored while the game is being played
        print(game.take_step('Julianne Moore', 'Colin Firth', 'A Single Man'))
        game_details = Gameplay.objects.all()
        print(game_details.values())

        # the details of the game should be updated and marked as complete when the game is solved
        self.assertEqual(game_details.values_list('start_contributor'), 'Cate Blanchett')





 
        
        