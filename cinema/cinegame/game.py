class Game:
    def __init__(self, start_node, end_node, ia):
        self.start_node = start_node
        self.end_node = end_node
        self.ia = ia
        self.moves = []

    def record(self, person, work):
        # record ids
        self.moves.append((person, work))

    def interpret_person(self, person):
        # return id corresponding to actor
        # or None
        # if at start of game, correct answer must be start_node
        # otherwise actor must be in cast of previous movie
        if len(self.moves):
            cast = set() # get cast from previous movie
        else:
            cast = {self.start_node}
        possible_people = set() # get possible ids from ia
        disambiguated = possible_people.intersection(cast)
        if len(disambiguated):
            return list(disambiguated)[0]
        return

    def interpret_work(self, work, person_id):
        # return is corresponding to movie
        # or None
        # must already have validated person
        if person_id is None:
            return
        possible_works = set() # look up from work
        known_works_from_person = set() # look up works from person
        works = possible_works.intersection(known_works_from_person)
        if len(works):
            return list
        pass

    def take_step(self, person, work):
        person_id = self.interpret_person(person)
        work_id = self.interpret_work(work, person_id)
        if work_id is None or person_id is None:
            return False
        else:
            self.record(person_id, work_id)
            return True
