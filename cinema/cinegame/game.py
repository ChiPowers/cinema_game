from datetime import datetime
import uuid

import imdb

from cinema.cinegraph.imdb_grapher import movie_actor_subgraph, s3_path_details
from cinema.cinegraph.grapher import PersonNode
from cinema.cinegraph.extractor import filmography_filter
from cinema.cinegraph.grapher import PersonNode, WorkNode

from cinema.gameplay.models import Gameplay


class Game:
    def __init__(self, start_id, end_id, moves=None):
        self.start_node = start_id
        self.end_node = end_id
        if moves is None:
            moves = []
        self.moves = moves

    def user(self):
        user = uuid.uuid1
        return user

    def fetch_possible_people(self, name):
        """
        Search database for people with name.
        :param name: string name of person.
        :return: set of IDs representing people
        """
        raise NotImplementedError()

    def fetch_contributors(self, work):
        """
        Search database for people who contributed to a work.
        :param work: ID representing a work
        :return: set of IDs representing contributors
        """
        raise NotImplementedError()

    def fetch_possible_works(self, title):
        """
        Search database for works with title.
        :param title: string title
        :return: set of IDs representing works
        """
        raise NotImplementedError()

    def fetch_works_for_person(self, person):
        """
        Search database for works to which a person contributed.
        :param person: ID representing a person
        :return: set of IDs representing works
        """
        raise NotImplementedError()

    def record(self, person0, person1, work):
        """
        Record IDs of people and works valid as next step
        @param person0: set of IDs representing people
        @param person1: set of IDs representing people
        @param work: set of IDs representing works
        """
        self.moves.append((person0, person1, work))

    def interpret_person(self, person, works):
        """
        Given name of a person and a set of works, search for IDs of any people
        with that name who contributed to one of those works
        @param person: string name
        @param works: set of IDs representing works
        @return: IDs of valid people with that name or empty set
        """
        contributors = set()
        for work in works:
            contributors.update(self.fetch_contributors(work))
        possible_people = self.fetch_possible_people(person)
        return possible_people.intersection(contributors)

    def interpret_work(self, work, people):
        """
        Given title of work and set of IDs representing people, search for IDs of
        any work with that name two which any of those people have contributed.
        @param work: as string title
        @param people: a set of contributors to the work
        @return: IDs of any valid movie with that title or empty set
        """
        possible_works = self.fetch_possible_works(work)
        known_works_from_people = set()
        for person_id in people:
            known_works_from_person = self.fetch_works_for_person(person_id)
            known_works_from_people.update(known_works_from_person)
        return possible_works.intersection(known_works_from_people)

    def take_step(self, person0, person1, work):
        start_time = datetime.utcnow()
        possible_people = self.fetch_possible_people(person0)
        if len(self.moves) == 0:
            if self.start_node not in possible_people:
                return False, "incorrect start"
            people0 = {self.start_node}
        else:
            _, previous_people, _ = self.moves[-1]
            people0 = possible_people.intersection(previous_people)
            if len(people0) == 0:
                end_time = datetime.utcnow()
                self.store_game_info(self, person0, person1, start_time, end_time)
                return False, "incorrect continuation"

        works = self.interpret_work(work, people0)
        if len(works) == 0:
            end_time = datetime.utcnow()
            self.store_game_info(self, person0, person1, start_time, end_time)
            return False, "person0 not in work"

        people1 = self.interpret_person(person1, works)
        if len(people1) == 0:
            end_time = datetime.utcnow()
            self.store_game_info(self, person0, person1, start_time, end_time)
            return False, "person1 not in work"

        self.record(people0, people1, works)

        if self.end_node in people1:
            end_time = datetime.utcnow()
            is_solved=True
            self.store_game_info(self, person0, person1, start_time, end_time, is_solved)
            return True, "you win"
        else:
            return True, "keep playing"

    def store_game_info(self, person0, person1, start_time, end_time, is_solved=False):
        # filled in the shortest path value to a constant until I determine the best way to generate the shortest path
        if Gameplay.objects.filter(user=self.user, start_contributor=person0, end_contributor=person1).exists():
            if is_solved:
                Gameplay.objects.filter(user=self.user, start_contributor=person0, end_contributor=person1).update(end_time=datetime.utcnow(), is_solved=is_solved, moves=self.moves)
            else:
                Gameplay.objects.filter(user=self.user, start_contributor=person0, end_contributor=person1).update(is_solved=is_solved, moves=self.moves)
        else:
            game_data = {
                "user" : self.user,
                "start_contributor": person0,
                "end_contributor": person1,
                "start_time": start_time,
                "end_time": datetime.utcnow(),
                "shortest_path": 3,
                "is_solved":is_solved,
                "moves": self.moves,
                }
            Gameplay.objects.create(**game_data)
        return



class GameIMDB(Game):
    def __init__(self, start_id, end_id, ia, moves=None):
        super().__init__(start_id, end_id, moves=moves)
        self.ia = ia

    def fetch_possible_people(self, name):
        return {int(person.getID()) for person in self.ia.search_person(name)}


class GameHTTPOnly(GameIMDB):
    def __init__(self, start_id, end_id, ia, moves=None):
        super().__init__(start_id, end_id, ia, moves=moves)

    def fetch_contributors(self, work):
        movie = self.ia.get_movie(work)
        return {int(actor.getID()) for actor in movie["cast"]}

    def fetch_works_for_person(self, person):
        person = self.ia.get_person(person, info="filmography")
        films = filmography_filter(person, roles=["actor", "actress"], kind="movie")
        return {int(film.getID()) for film in films}

    def fetch_possible_works(self, title):
        possible_works = self.ia.search_movie(title)
        return {int(work.getID()) for work in possible_works if work["kind"] == "movie"}


class GameGraphAndS3(GameIMDB):
    def __init__(self, start_id, end_id, g, ia, moves=None):
        super().__init__(start_id, end_id, ia, moves=moves)
        self.g = g

    def fetch_neighbors(self, node):
        return {node.id for node in self.g.neighbors(node)}

    def fetch_contributors(self, work):
        return self.fetch_neighbors(WorkNode(work))

    def fetch_works_for_person(self, person):
        return self.fetch_neighbors(PersonNode(person))

    def fetch_possible_works(self, title):
        possible_works = self.ia.search_movie(title)
        return {int(work.getID()) for work in possible_works}


class GameGraphAndHTTP(GameGraphAndS3):
    def __init__(self, start_id, end_id, g, ia, moves=None):
        super().__init__(start_id, end_id, g, ia, moves=moves)

    def fetch_possible_works(self, title):
        possible_works = self.ia.search_movie(title)
        return {int(work.getID()) for work in possible_works if work["kind"] == "movie"}
