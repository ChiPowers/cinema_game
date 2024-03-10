from datetime import datetime
import uuid

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
        return str(user)

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
        game_data = {
            "user": self.user,
            "start_contributor": self.start_node,
            "end_contributor": self.end_node,
            "start_time": datetime.utcnow(),
        }

        possible_people = self.fetch_possible_people(person0)
        if len(self.moves) == 0:
            if self.start_node not in possible_people:
                return False, "incorrect start"
            people0 = {self.start_node}
        else:
            _, previous_people, _ = self.moves[-1]
            people0 = possible_people.intersection(previous_people)
            if len(people0) == 0:
                game_data["end_time"] = datetime.utcnow()
                self.store_game_info(game_data)
                return False, "incorrect continuation"

        works = self.interpret_work(work, people0)
        if len(works) == 0:
            game_data["end_time"] = datetime.utcnow()
            self.store_game_info(game_data)
            return False, "person0 not in work"

        people1 = self.interpret_person(person1, works)
        if len(people1) == 0:
            game_data["end_time"] = datetime.utcnow()
            self.store_game_info(game_data)
            return False, "person1 not in work"

        self.record(people0, people1, works)

        if self.end_node in people1:
            game_data["is_solved"] = True
            game_data["end_time"] = datetime.utcnow()
            self.store_game_info(game_data)
            return True, "you win"
        else:
            return True, "keep playing"

    def store_game_info(self, game_data):
        game_to_store = Gameplay.objects.filter(
            user=game_data["user"],
            start_contributor=game_data["start_contributor"],
            end_contributor=game_data["end_contributor"],
        )
        if game_to_store.exists():
            if game_data["is_solved"]:
                moves_dict = self.convert_moves_to_dict()
                game_to_store.update(
                    end_time=game_data["end_time"],
                    is_solved=game_data["is_solved"],
                    moves=moves_dict,
                )
            else:
                moves_dict = self.convert_moves_to_dict()
                game_to_store.update(moves=moves_dict)
        else:
            moves_dict = self.convert_moves_to_dict()
            game_data["moves"] = moves_dict

            # compute the shortest path between actors
            # this makes the final step really slow
            # must find a better place for this or make it async
            # with open('professional_graph05.pkl', 'rb') as f:
            #     g = pickle.load(f)
            # g = movie_actor_subgraph(g)
            # game_data['shortest_path'] = nx.shortest_path_length(
            #     g, PersonNode(game_data['start_contributor']), \
            #         PersonNode(game_data['end_contributor'])
            #         )//2
            game_data["shortest_path"] = 3
            # store the gameplay data
            Gameplay.objects.create(**game_data)
        return

    def convert_moves_to_dict(self):
        moves_dict = dict()
        for i, item in enumerate(self.moves):
            moves_dict[i] = str(item)
        if len(moves_dict) < 1:
            moves_dict["0"] = "fail"
        return moves_dict


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
