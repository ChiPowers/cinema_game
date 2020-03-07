from django.db import models
import jsonfield

class Gameplay(models.Model):
    # account of person playing the game - should be foreignkey field
    user = models.CharField(max_length=200)
    # id of the game - should be foreignkey field 
    game = models.CharField(max_length=200)
    # start/source actor or contributor to the work
    start_contributor = models.CharField(max_length=200)
    # end/target actor or contritor to the work
    end_contributor = models.CharField(max_length=200)
    # time of game start
    start_time = models.DateTimeField('game start time', null=True)
    # time of game end
    end_time = models.DateTimeField('game end time', null=True)
    # shortest number of steps between start and end contributors
    shortest_path = models.IntegerField()
    # indicates whether this game is solved
    is_solved = models.BooleanField(default = False)
    # moves stored as dict in jsonfield
    moves = jsonfield.JSONField(default=dict(), null=True, blank=True)