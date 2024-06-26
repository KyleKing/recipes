"""Invoke Tasks."""

from pathlib import Path

from beartype import beartype
from calcipy.cli import task
from calcipy.invoke_helpers import run
from calcipy.tasks.all_tasks import _MAIN_TASKS, ns, with_progress  # noqa: PLC2701
from corallium.log import LOGGER
from invoke.context import Context
from PIL import Image

from .formatter import format_recipes as formatter_format_recipes
from .formatter import get_recipes_doc_dir


@task()
def format_recipes(_ctx: Context) -> None:
    """Format recipes."""
    formatter_format_recipes()


@beartype
def _convert_png_to_jpg(dir_md: Path) -> None:
    """Convert any remaining PNG files to jpg."""
    for path_png in dir_md.glob('*/*.png'):
        if path_png.parent.name != '_icons':
            LOGGER.warning('Convert to jpg and deleting original', path_png=path_png)
            Image.open(path_png).save(path_png.parent / f'{path_png.stem}.jpg')
            path_png.unlink()


_OPTIMIZE_CMD = 'poetry run optimize-images -mh 900 --convert-all --force-delete'
"""Command for optimize-images run from poetry. Requires the path to the folder or image."""


@task()
def convert_png_to_jpg(_ctx: Context) -> None:
    """Convert PNG images to JPG."""
    _convert_png_to_jpg(dir_md=get_recipes_doc_dir())


@task(
    pre=[convert_png_to_jpg],
)
def compress_all(ctx: Context) -> None:
    """Compress images."""
    run(ctx, f'{_OPTIMIZE_CMD} {get_recipes_doc_dir()}/')


@task()
def compress(ctx: Context) -> None:
    """Compress one or more specific images."""
    for file_arg in ctx.config.gto.file_args:
        run(ctx, f'{_OPTIMIZE_CMD} {file_arg}')


ns.add_task(format_recipes)
ns.add_task(convert_png_to_jpg)
ns.add_task(compress_all)
ns.add_task(compress)


@task(post=with_progress([format_recipes, *_MAIN_TASKS]))
def main(_ctx: Context) -> None:
    """Override the main task pipeline."""


ns.add_task(main)
