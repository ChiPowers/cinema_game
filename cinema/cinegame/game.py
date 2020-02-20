from cinema.cinegraph.extractor import filmography_filter


class Game:
    def __init__(self, start_id, end_id, ia):
        self.start_node = start_id
        self.end_node = end_id
        self.moves = []
        self.ia = ia

    def record(self, person, work):
        """
        Record IDs of people and works valid as next step
        @param person: set of IDs representing people
        @param work: set of IDs representing works
        """
        self.moves.append((person, work))

    def interpret_person(self, person):
        """
        Given name of a person, search for ID of any people with that name
        who could be part of a valid next step. If at start of game, correct
        answer must be start_node. Otherwise person must be a contributor to
        a work from a previous step.
        @param person: string name
        @return: IDs of valid people with that name or empty set
        """
        if len(self.moves):
            cast = set()
            _, works = self.moves[-1]
            for work_id in works:
                movie = self.ia.get_movie(work_id)
                actors = [actor.getID() for actor in movie['cast']]
                cast.update(actors)
        else:
            cast = {self.start_node}
        possible_people = set(self.ia.search_people(person))
        return possible_people.intersection(cast)

    def interpret_work(self, work, people):
        """
        Assumes that person is already validated as a set of
        @param work: as string title
        @param people: a set of contributors to the work
        @return: IDs of any valid movie with that title or empty set
        """
        possible_works = self.ia.search_movie(work)
        possible_works = {work for work in possible_works if work['kind'] == 'movie'}
        known_works_from_people = set()
        for person_id in people:
            person = self.ia.get_person(person_id, info='filmography')
            films = filmography_filter(person, roles=['actor', 'actress'], kind='movie')
            known_works_from_person = {film.getID() for film in films} # look up works from person
            known_works_from_people.update(known_works_from_person)
        return possible_works.intersection(known_works_from_people)

    def take_step(self, person, work):
        person_id = self.interpret_person(person)
        work_id = self.interpret_work(work, person_id)
        if work_id is None or person_id is None:
            return False
        else:
            self.record(person_id, work_id)
            return True
