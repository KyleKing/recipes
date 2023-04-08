from pathlib import Path
from unittest.mock import call

from calcipy.cli import GlobalTaskOptions

from recipes.tasks import compress, format_recipes


def test_format_recipes(ctx):
    format_recipes(ctx)

    ctx.run.assert_has_calls([])


def test_compress(ctx):
    ctx.config.gto = GlobalTaskOptions(file_args=[Path('example.png')])

    compress(ctx)

    ctx.run.assert_has_calls([
        call('poetry run optimize-images -mh 900 --convert-all --force-delete example.png'),
    ])
