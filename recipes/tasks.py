"""Doit Tasks for the MKDocs project."""

import webbrowser

from calcipy.doit_tasks.base import debug_task
from calcipy.doit_tasks.doit_globals import DoItTask
from doit.tools import LongRunning
from loguru import logger
from PIL import Image

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


def _convert_png_to_jpg() -> None:
    """Convert any remaining PNG files to jpg."""
    for path_png in DIR_MD.glob('*/*.png'):
        logger.warning(f'COnvert to jpg and deleting original for: {path_png}')
        Image.open(path_png).save(path_png.parent / f'{path_png.stem}.jpg')
        path_png.unlink()


# TODO: Add keyword argument for path to a single image to reduce impact on git
def task_compress() -> DoItTask:
    """Compress images.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        LongRunning(f'poetry run optimize-images {DIR_MD}/ -mh 700 -mh 900 --convert-all --force-delete'),
        (_convert_png_to_jpg, ),
    ])
