from django.db import models


import json


class Gameplay(models.Model):
    id = models.AutoField(primary_key=True)

    # account id of person playing the game - will be foreign key
    user = models.CharField(max_length=200, default="test_user")

    # start/source actor or contributor to the work
    start_contributor = models.CharField(max_length=200)

    # end/target actor or contritor to the work
    end_contributor = models.CharField(max_length=200)

    # time of game start
    start_time = models.DateTimeField("game start time", null=True)

    # time of game end
    end_time = models.DateTimeField("game end time", null=True)

    # shortest number of steps between start and end contributors
    shortest_path = models.IntegerField()

    # indicates whether this game is solved
    is_solved = models.BooleanField(default=False)

    moves_json = models.TextField(default="{}", null=True, blank=True)

    # moves stored as dict in jsonfield
    @property
    def moves(self) -> dict:
        return json.loads(self.moves_json)

    @moves.setter
    def moves(self, value: dict):
        self.moves_json = json.dumps(value)

    class Meta:
        app_label = "gameplay"
