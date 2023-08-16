"""Start the command line program."""

from . import __pkg_name__, __version__


def start() -> None:
    """Run the customized Invoke Program."""
    from calcipy.cli import start_program

    from . import tasks

    start_program(__pkg_name__, __version__, tasks)
