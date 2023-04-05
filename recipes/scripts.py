"""Start the command line program."""

from beartype import beartype
from calcipy.cli import start_program

from . import __pkg_name__, __version__


@beartype
def start() -> None:  # pragma: no cover
    """Run the customized Invoke Program."""
    from . import tasks
    start_program(__pkg_name__, __version__, tasks)
