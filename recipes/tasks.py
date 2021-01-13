"""Doit Tasks for the MKDocs project."""

import shlex
import subprocess  # noqa S404
import webbrowser
from typing import List

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
        (webbrowser.open, ('http://localhost:8000',)),
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
        logger.warning(f'Convert to jpg and deleting original for: {path_png}')
        Image.open(path_png).save(path_png.parent / f'{path_png.stem}.jpg')
        path_png.unlink()


_OPTIMIZE_CMD = 'poetry run optimize-images -mh 700 -mh 900 --convert-all --force-delete'
"""Command for optimize-images run from poetry. Requires the path to the folder or image."""


def task_compress_all() -> DoItTask:
    """Compress images.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        (_convert_png_to_jpg,),
        LongRunning(f'{_OPTIMIZE_CMD} {DIR_MD}/'),
    ])


def task_convert_png_to_jpg() -> DoItTask:
    """Convert PNG images to JPG.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        (_convert_png_to_jpg,),
    ])


def task_compress() -> DoItTask:
    """Compress one or more specific images.

    Example: `doit run compress -f ./docs/dessert/biscotti.jpg`

    Returns:
        DoItTask: DoIt task

    """
    def _run_params(pos: List[str]) -> None:
        for pos_arg in pos:
            subprocess.run(shlex.split(f'{_OPTIMIZE_CMD} {pos_arg}'), check=True)  # noqa S603

    task = debug_task([(_run_params,)])  # _OPTIMIZE_CMD + ' %(pos)s'])
    task['pos_arg'] = 'pos'
    return task
