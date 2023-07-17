"""Start the command line program."""

from beartype import beartype

from . import __pkg_name__, __version__


@beartype
def start() -> None:
    """Run the customized Invoke Program."""
    from calcipy.cli import start_program

    from . import tasks

    start_program(__pkg_name__, __version__, tasks)
