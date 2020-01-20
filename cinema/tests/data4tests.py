class MockImdbObject(dict):
    __id = "000000"

    def __init__(self, *args, default=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = default

    def __missing__(self, key):
        return self.default

    def getID(self):
        return self.__id


# Kevin Bacon
def get_bacon(ia=None):
    return ia.get_person("0000102", info=("main", "filmography", "biography"))


# Natalie Portman
def get_natalie(ia=None):
    return ia.get_person("0000204", info=("main", "filmography", "biography"))


# Sarah Michelle Gellar
def get_sarah(ia=None):
    return ia.get_person("0001264", info=("main", "filmography", "biography"))


# The Air I Breath
def get_air(ia=None):
    return ia.get_movie("0485851")


# A Powerful Noise Live
def get_noise(ia=None):
    return ia.get_movie("1392211")
