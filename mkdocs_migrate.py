"""Convert JSON files to markdown for mkdocs."""

import json
import shutil
from collections import defaultdict
from copy import copy
from pathlib import Path
from typing import Iterable, List, Union

from loguru import logger

ICON_FA_STAR = ':fontawesome-solid-star:'
ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
ICON_M_STAR = ':material-star:'
ICON_M_STAR_OUT = ':material-star-outline:'
ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'
ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'


def format_source(source: str) -> str:
    """Format the source string."""  # noqa
    if source and source.startswith('http'):
        return f'\n\n> Based on [{source}]({source})'
    elif source:
        return f'\n\n> Based on {source}'
    return ''


def format_md_list(iterator: Union[dict, Iterable], list_prefix: str = '-') -> List[str]:
    """Recursively format a markdown list interpretting a dictionary as a multi-level list."""  # noqa
    out = []
    logger.debug('({type_iter}) iterator={iterator}', iterator=iterator, type_iter=type(iterator))
    if isinstance(iterator, dict):
        for key, values in iterator.items():
            logger.debug('{key}: ({type_values}) {values}', key=key, values=values, type_values=type(values))
            out.append(f'{list_prefix} {key}')
            out.extend(format_md_list(values, '  ' + list_prefix))
    else:
        out.extend([f'{list_prefix} {value}' for value in iterator])
    logger.debug('Created: {out}', out=out)
    return out


def format_md_task_list(iterator: Union[dict, Iterable]) -> List[str]:
    """Run format_md_list with the default list prefix set to a check or task list format."""  # noqa
    logger.info('Starting "format_md_task_list": {iterator}', iterator=iterator)
    return format_md_list(iterator, list_prefix='- [ ]')


def image_html(path_image: str) -> str:
    """Format the image link as markdown."""  # noqa
    return '\n'.join([
        '<!-- Start:Image (WIP: Placeholder) -->',
        '![loading...recipe-breakfast_burrito](/imgs/breakfast-breakfast_burrito.jpeg){: .image-recipe loading=lazy }'
        '<!-- End:Image (WIP: Placeholder) -->',
    ])


def md_from_json(filename: str, recipe: dict) -> str:
    """Convert the JSON files to a markdown string for MKDocs."""  # noqa
    title = filename.replace('_', ' ').title()
    stars = ' '.join([ICON_FA_STAR] * recipe['rating'] + [ICON_FA_STAR_OUT] * (5 - recipe['rating']))
    image = image_html('TBD')  # HACK: need to locate the image file, which will be copied for migration
    # ^ also ensure that all images in database/ are copied too
    sections = [
        '<!-- Do not modify. Auto-generated with mkdocs_migrate.py -->',
        f'# {title}' + format_source(recipe['source']),
        'Personal rating: ' + stars,
        image,
        '## Ingredients',
        '\n'.join(format_md_task_list(recipe['ingredients'])),
        '## Recipe',
        '\n'.join(format_md_list(recipe['recipe'])),
    ]
    if recipe['notes']:
        sections.extend([
            '## Notes',
            '\n'.join(format_md_list(recipe['notes'])),
        ])
    return '\n\n'.join(sections) + '\n'


if __name__ == '__main__':
    """Convert all JSON files to markdown."""
    CWD = Path(__file__).resolve().parent
    dir_json = CWD / 'database'
    dir_md = CWD / 'docs'

    sub_dir_count = defaultdict(lambda: 0)
    for path_json in dir_json.glob('*/*.json'):
        sub_dir = path_json.parent.name
        sub_dir_count[sub_dir] += 1
        logger.info(f'{sub_dir}||{path_json.stem}')
        recipe_data = json.loads(path_json.read_text())
        if sub_dir_count[sub_dir] < 5:
            try:
                path_md = dir_md / sub_dir / f'{path_json.stem}.md'
                (path_md.parent).mkdir(exist_ok=True, parents=True)
                # TODO: 1-Copy and link the image

                path_md.write_text(md_from_json(path_json.stem, recipe_data))
            except Exception:
                from pprint import pprint
                pprint(recipe_data)  # noqa: T003
                raise
    logger.info(sub_dir_count)
    # TODO: 2-Test `mkdocs gh-deploy`

# TODO: Consider making an aggregate page so that the recipes are easier to find
#   ^ possibly just photos and names for a better TOC
