"""Check that all imports work as expected in the built package."""

from pprint import pprint

from recipes.scripts import run

pprint(locals())  # noqa: T203
