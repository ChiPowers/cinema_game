from cinema.cinegraph.extractor import filmography_filter


class Game:
    def __init__(self, start_id, end_id, ia):
        self.start_node = start_id
        self.end_node = end_id
        self.moves = []
        self.ia = ia

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
        for work_id in works:
            movie = self.ia.get_movie(work_id)
            actors = [int(actor.getID()) for actor in movie['cast']]
            contributors.update(actors)
        possible_people = {int(person.getID()) for person in self.ia.search_person(person)}
        return possible_people.intersection(contributors)

    def interpret_work(self, work, people):
        """
        Given title of work and set of IDs representing people, search for IDs of
        any work with that name two which any of those people have contributed.
        @param work: as string title
        @param people: a set of contributors to the work
        @return: IDs of any valid movie with that title or empty set
        """
        possible_works = self.ia.search_movie(work)
        possible_works = {int(work.getID()) for work in possible_works if work['kind'] == 'movie'}
        known_works_from_people = set()
        for person_id in people:
            person = self.ia.get_person(person_id, info='filmography')
            films = filmography_filter(person, roles=['actor', 'actress'], kind='movie')
            known_works_from_person = {int(film.getID()) for film in films} # look up works from person
            known_works_from_people.update(known_works_from_person)
        return possible_works.intersection(known_works_from_people)

    def take_step(self, person0, person1, work):
        possible_people = {int(person.getID()) for person in self.ia.search_person(person0)}
        if len(self.moves) == 0:
            if self.start_node not in possible_people:
                return False, 'incorrect start'
            people0 = {self.start_node}
        else:
            _, previous_people, _ = self.moves[-1]
            people0 = possible_people.intersection(previous_people)
            if len(people0) == 0:
                return False, 'incorrect continuation'

        works = self.interpret_work(work, people0)
        if len(works) == 0:
            return False, 'person0 not in work'

        people1 = self.interpret_person(person1, works)
        if len(people1) == 0:
            return False, 'person1 not in work'

        self.record(people0, people1, works)

        if self.end_node in people1:
            return True, 'you win'
        else:
            return True, 'keep playing'
