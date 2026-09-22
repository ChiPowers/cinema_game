"""Check that optional dependencies stay behind a boundary.

An optional dependency should be imported by at most one library module. That
module owns the dependency: it defines the interface the rest of the code uses,
implements it, and hands out instances. Everything else receives an
implementation by injection and never imports the dependency itself.

Scope is taken from the project's own declaration: packages in Poetry groups
marked `optional = true`, plus every extra, in either the PEP 621
`[project.optional-dependencies]` form or the older `[tool.poetry.extras]`
form. Extras matter most -- Poetry groups never appear in wheel metadata, so a
library's consumer-facing optional dependencies are always extras.

Core dependencies are deliberately out of scope: spreading pandas across ten
modules is normal, spreading an optional service client across ten modules is a
missing boundary.

A project's own distribution is never watched, so the self-referential
`all = ["mypkg[anthropic]"]` idiom does not cause the project to police its own
intra-package imports.

Matching is on dotted module paths, not first segments. This matters for PEP 420
namespace packages: `google` is shared by `google-genai`, `google-cloud-storage`
and `google-auth`, so collapsing to the first segment would count unrelated
distributions as one and invent leaks.

Entry points are exempt. Wiring concrete implementations together is what an
entry point is for.

Known limitation: PEP 735 `[dependency-groups]` is NOT read. A project using
that form gets a vacuous pass -- the check reports "nothing to check" and exits
0. Treat that message with suspicion on any project you know has optional
dependencies, and extend `optional_dependencies()` rather than trusting it.
(A different exit-0 message, naming the excluded distributions, means extras
were found but every one is also a core dependency -- that one is legitimate.)

Usage:  python scripts/import_boundaries.py [project_root]
Exit:   0 if every optional dependency is isolated, 1 otherwise.
"""

import ast
import os
import re
import sys
import tomllib
from collections import defaultdict

ENTRY_FILES = ("main.py", "cli.py", "__main__.py", "app.py")
ENTRY_DIRS = ("scripts", "bin", "notebooks")

# Canonical distribution name -> dotted module path, where they differ.
# Entries mapping into a shared namespace package MUST give the full dotted
# path: `google-genai` is imported as `google.genai`, and mapping it to bare
# `google` would also match `google.cloud.*` and `google.auth` from entirely
# different distributions.
ALIASES = {
    "beautifulsoup4": "bs4",
    "google-genai": "google.genai",
    "google-generativeai": "google.generativeai",
    "opencv-python": "cv2",
    "pillow": "PIL",
    "python-dotenv": "dotenv",
    "pyyaml": "yaml",
    "scikit-learn": "sklearn",
}


def canonical(distribution):
    """PEP 503 normalized distribution name, for comparing declarations."""
    return re.sub(r"[-_.]+", "-", distribution).lower()


def module_name(distribution):
    key = canonical(distribution)
    return ALIASES.get(key, key.replace("-", "_"))


def own_names(config):
    """Canonical names that refer to this project, not to a dependency."""
    poetry = config.get("tool", {}).get("poetry", {})
    names = set()
    for name in (config.get("project", {}).get("name"), poetry.get("name")):
        if name:
            names.add(canonical(name))
    for package in poetry.get("packages", []):
        if isinstance(package, dict) and package.get("include"):
            names.add(canonical(package["include"]))
    return names


def is_entry_point(relative_path):
    parts = relative_path.split(os.sep)
    return os.path.basename(relative_path) in ENTRY_FILES or parts[0] in ENTRY_DIRS


def requirement_name(requirement):
    """Leading distribution name of a PEP 508 requirement string."""
    # `@` is included because PEP 508 permits `name@ url` with no space.
    return re.split(r"[\s\[(<>=!~;@]", requirement.strip(), maxsplit=1)[0]


def core_dependency_names(config):
    """Canonical names declared as core (non-optional) dependencies.

    Per the module docstring, core dependencies are out of scope for this
    check: spreading pandas across ten modules is normal, spreading an
    optional service client across ten modules is a missing boundary. A
    distribution can appear in `[project.optional-dependencies]` purely as
    the carrier of a *vendor* extra (`mypkg = ["reusable-llm-provider[anthropic]"]`)
    while itself being declared a core dependency in `[project.dependencies]`
    -- that does not make the carrier optional, so it must not be watched.
    """
    poetry = config.get("tool", {}).get("poetry", {})
    names = set()

    for requirement in config.get("project", {}).get("dependencies", []):
        distribution = requirement_name(requirement)
        if distribution:
            names.add(canonical(distribution))

    # Older Poetry-style `[tool.poetry.dependencies]` entries are core unless
    # explicitly marked `optional = true`.
    for distribution, spec in poetry.get("dependencies", {}).items():
        if distribution == "python":
            continue
        if isinstance(spec, dict) and spec.get("optional"):
            continue
        names.add(canonical(distribution))

    return names


def optional_dependencies(root):
    with open(os.path.join(root, "pyproject.toml"), "rb") as handle:
        config = tomllib.load(handle)
    poetry = config.get("tool", {}).get("poetry", {})
    mine = own_names(config)
    core = core_dependency_names(config)
    names = set()
    # Distributions that WOULD have been watched but are excluded because
    # they are also core dependencies (see core_dependency_names()). Tracked
    # separately so check() can tell "nothing declared" apart from
    # "declared, but every one of them is out of scope."
    excluded_as_core = set()

    # Poetry groups marked optional (developer-facing)
    for group in poetry.get("group", {}).values():
        if not group.get("optional"):
            continue
        for distribution in group.get("dependencies", {}):
            if distribution == "python":
                continue
            if canonical(distribution) in core:
                excluded_as_core.add(module_name(distribution))
                continue
            names.add(module_name(distribution))

    # PEP 621 extras (consumer-facing; these are what reach wheel metadata)
    for requirements in (
        config.get("project", {}).get("optional-dependencies", {}).values()
    ):
        for requirement in requirements:
            distribution = requirement_name(requirement)
            # `all = ["mypkg[anthropic]"]` refers to this project, not a dep.
            if not distribution or canonical(distribution) in mine:
                continue
            # A distribution that is itself a core dependency (declared in
            # `[project.dependencies]`) is only appearing here as the carrier
            # of a vendor extra -- see core_dependency_names().
            if canonical(distribution) in core:
                excluded_as_core.add(module_name(distribution))
                continue
            names.add(module_name(distribution))

    # Legacy Poetry extras
    for distributions in poetry.get("extras", {}).values():
        for distribution in distributions:
            distribution = requirement_name(distribution)
            if not distribution or canonical(distribution) in mine:
                continue
            if canonical(distribution) in core:
                excluded_as_core.add(module_name(distribution))
                continue
            names.add(module_name(distribution))

    return names, excluded_as_core


def imported_modules(path):
    try:
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
    except (OSError, SyntaxError):
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module
            # `from google import genai` keeps the submodule in the alias, so
            # the dotted path is only recoverable by joining the two. An alias
            # may name an attribute rather than a submodule; that yields a
            # candidate which simply matches nothing.
            for alias in node.names:
                if alias.name != "*":
                    yield f"{node.module}.{alias.name}"


def source_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full = os.path.join(dirpath, filename)
            relative = os.path.relpath(full, root)
            if "tests" in relative.split(os.sep):
                continue
            yield full, relative


def covers(imported, watched):
    """True if a dotted import path falls under a watched module path."""
    return imported == watched or imported.startswith(watched + ".")


def check(root):
    watched, excluded_as_core = optional_dependencies(root)
    if not watched:
        if excluded_as_core:
            print(
                "Declared optional distributions are all also core dependencies "
                f"({', '.join(sorted(excluded_as_core))}), so they are out of "
                "scope per this check's stated scope; nothing to watch."
            )
        else:
            print("No optional dependency groups or extras declared; nothing to check.")
        return 0

    importers = defaultdict(lambda: {"library": set(), "entry": set()})
    for full, relative in source_files(root):
        key = "entry" if is_entry_point(relative) else "library"
        for imported in imported_modules(full):
            for module in watched:
                if covers(imported, module):
                    importers[module][key].add(relative)

    violations = 0
    for module in sorted(watched):
        sites = importers[module]
        library = sorted(sites["library"])
        entry = sorted(sites["entry"])
        if not library and not entry:
            # Not a failure -- a declared extra may simply be unused. But it is
            # also what a wrong ALIASES mapping looks like, so say so rather
            # than printing a reassuring "ok".
            print(
                f"--    {module}: never imported "
                f"(unused, or the ALIASES mapping is wrong)"
            )
            continue
        if len(library) <= 1:
            plural = "" if len(library) == 1 else "s"
            print(
                f"ok    {module}: {len(library)} library module{plural}, "
                f"{len(entry)} entry point(s)"
            )
            continue
        violations += 1
        print(f"LEAK  {module}: imported by {len(library)} library modules")
        for path in library:
            print(f"        {path}")

    if violations:
        print(
            f"\n{violations} optional dependency/dependencies are not isolated.\n"
            "Put the dependency behind one module that owns it and inject the\n"
            "result, or declare it non-optional if it is genuinely core."
        )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else "."))
