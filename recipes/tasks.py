"""Doit Tasks for the MKDocs project."""

import shlex
import subprocess  # nosec # noqa S404
import sys

from beartype import beartype
from calcipy.doit_tasks.base import debug_task
from calcipy.doit_tasks.doit_globals import DoitTask
from doit.tools import Interactive
from loguru import logger
from PIL import Image

from .formatter import DIR_MD, format_recipes

# Log the positional arguments to help with debugging tasks if needed
logger.debug('sys.argv={sys_argv}', sys_argv=sys.argv)


@beartype
def task_format_recipes() -> DoitTask:
    """Format recipes.

    Returns:
        DoitTask: DoIt task

    """
    return debug_task([(format_recipes, ())])


@beartype
def _convert_png_to_jpg() -> None:
    """Convert any remaining PNG files to jpg."""
    for path_png in DIR_MD.glob('*/*.png'):
        if path_png.parent.name != '_icons':
            logger.warning(f'Convert to jpg and deleting original for: {path_png}')
            Image.open(path_png).save(path_png.parent / f'{path_png.stem}.jpg')
            path_png.unlink()


_OPTIMIZE_CMD = 'poetry run optimize-images -mh 900 --convert-all --force-delete'
"""Command for optimize-images run from poetry. Requires the path to the folder or image."""


@beartype
def task_compress_all() -> DoitTask:
    """Compress images.

    Returns:
        DoitTask: DoIt task

    """
    return debug_task([
        (_convert_png_to_jpg,),
        Interactive(f'{_OPTIMIZE_CMD} {DIR_MD}/'),
    ])


@beartype
def task_convert_png_to_jpg() -> DoitTask:
    """Convert PNG images to JPG.

    Returns:
        DoitTask: DoIt task

    """
    return debug_task([
        (_convert_png_to_jpg,),
    ])


@beartype
def task_compress() -> DoitTask:
    """Compress one or more specific images.

    Example: `poetry run doit run compress ./docs/dessert/biscotti.jpg`

    Returns:
        DoitTask: DoIt task

    """
    def _run_params(pos: list[str]) -> None:
        for pos_arg in pos:
            cmds = shlex.split(f'{_OPTIMIZE_CMD} {pos_arg}')
            logger.info('Running: {cmds}', cmds=cmds)
            subprocess.run(cmds, check=True)  # nosec # noqa S603

    task = debug_task([(_run_params,)])  # _OPTIMIZE_CMD + ' %(pos)s'])
    task['pos_arg'] = 'pos'
    return task
