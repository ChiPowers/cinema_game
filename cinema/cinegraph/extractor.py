def kind_filter(works, kind="movie"):
    return [work for work in works if work["kind"] == kind]


def filmography_filter(person, roles=None, kind=None):
    filmography = person['filmography']
    if roles is not None:
        if type(roles) == str:
            roles = {roles}
        else:
            roles = set(roles)
    else:
        roles = set(filmography.keys())
    works = []
    for role in roles:
        works += filmography[role]
    if kind is not None:
        works = kind_filter(works, kind=kind)
    return works


def work_intersection(works0, works1):
    ids0 = {work.getID() for work in works0}
    ids1 = {work.getID() for work in works1}
    ids = ids0.intersection(ids1)
    return [work for work in works0 if work.getID() in ids]
