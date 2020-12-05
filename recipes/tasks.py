"""Doit Tasks for the MKDocs project."""

import webbrowser

from dash_dev.doit_helpers.base import debug_task
from dash_dev.doit_helpers.doit_globals import DoItTask
from doit.tools import LongRunning

from .formatter import DIR_MD


def task_main() -> DoItTask:
    """Format markdown files.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([LongRunning('poetry run python main.py')])


def task_serve() -> DoItTask:
    """Serve the recipe site with `--dirtyreload` and open in a web browser.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        (webbrowser.open, ('http://localhost:8000', )),
        LongRunning('poetry run mkdocs serve --dirtyreload'),
    ])


def task_deploy() -> DoItTask:
    """Deploy to Github `gh-pages` branch.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([LongRunning('poetry run mkdocs gh-deploy')])


def task_compress() -> DoItTask:
    """Compress images.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        LongRunning(f'poetry run optimize-images {DIR_MD}/ -mh 700 -mh 900'),
        # TODO: --convert-all
        # TODO: progressive JPEG?
    ])
