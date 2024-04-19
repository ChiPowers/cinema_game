class ProfessionalNode:
    id: int | str
    is_person: bool

    def __init__(self, id: int | str, is_person: bool):
        self.id = id
        self.is_person = is_person

    def __hash__(self):
        return hash(self.id) + hash(self.is_person)

    def __eq__(self, other):
        return self.id == other.id and self.is_person == other.is_person

    @property
    def description_str(self):
        return "person" if self.is_person else "work"

    def __str__(self):
        return "<{} {}>".format(self.description_str, self.id)

    def __repr__(self):
        return "ProfessionalNode({}, {})".format(repr(self.id), bool(self.is_person))


class PersonNode(ProfessionalNode):
    def __init__(self, id):
        ProfessionalNode.__init__(self, id, True)

    def __repr__(self):
        return "PersonNode({})".format(repr(self.id))


class WorkNode(ProfessionalNode):
    def __init__(self, id):
        ProfessionalNode.__init__(self, id, False)

    def __repr__(self):
        return "WorkNode({})".format(repr(self.id))
