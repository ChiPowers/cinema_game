import uuid
from datetime import datetime, date

from django.test import TestCase
from .models import Gameplay

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
        
        
        