"""Path resolution utilities for cinema_game_backend.

Provides helper functions to locate code, base, secrets, and test directories
relative to the package structure.
"""

import os


def qualifyname(directoryname, filename=None):
    """Qualify a filename within a directory."""
    if filename is None:
        return directoryname
    return os.path.join(directoryname, filename)


def code(filename=None):
    """Get path within the cinema_game_backend package directory."""
    codepath = os.path.dirname(__file__)
    return qualifyname(codepath, filename)


def base(filename=None):
    """Get path within the repo base directory (parent of cinema_game_backend)."""
    basepath = os.path.abspath(code(".."))
    return qualifyname(basepath, filename)


def secrets(filename=None):
    """Get path within the secrets directory (repo root/secrets)."""
    return qualifyname(base("secrets"), filename)


def tests(filename=None):
    """Get path within the tests directory."""
    return qualifyname(code("tests"), filename)
