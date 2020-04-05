import os


def base(p=None):
    here = os.path.abspath(__file__)
    dir = os.path.dirname(here)
    if p is None:
        return dir
    return os.path.join(dir, p)


def test(p=None):
    dir = base("tests")
    if p is None:
        return dir
    return os.path.join(dir, p)


def data(p=None):
    dir = os.path.abspath(base(".."))
    dir = os.path.join(dir, "data")
    if p is None:
        return dir
    return os.path.join(dir, p)
