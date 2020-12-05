"""Convert JSON files to markdown for mkdocs."""

import json
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Union

from loguru import logger

logger.remove()
logger.add(sys.stdout, level='INFO')

CWD = Path(__file__).resolve().parent
DIST_IMG = CWD / 'dist/imgs'

ICON_FA_STAR = ':fontawesome-solid-star:'
ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
ICON_M_STAR = ':material-star:'
ICON_M_STAR_OUT = ':material-star-outline:'
ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'  # noqa: P103
ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'  # noqa: P103


def format_source(source: str) -> str:
    """Format the source string."""  # noqa
    if source and source.startswith('http'):
        return f'\n\n> Based on [{source}]({source})'
    elif source:
        return f'\n\n> Based on {source}'
    return ''


def format_md_list(iterator: Union[dict, Iterable], list_prefix: str = '*') -> List[str]:
    """Recursively format a markdown list interpretting a dictionary as a multi-level list."""  # noqa
    out = []
    logger.debug('({type_iter}) iterator={iterator}', iterator=iterator, type_iter=type(iterator))
    if isinstance(iterator, dict):
        for key, values in iterator.items():
            logger.debug('{key}: ({type_values}) {values}', key=key, values=values, type_values=type(values))
            out.append(f'{list_prefix} {key}')
            out.extend(format_md_list(values, '    ' + list_prefix))
    else:
        out.extend([f'{list_prefix} {value}' for value in iterator])
    logger.debug('Created: {out}', out=out)
    return out


def format_md_task_list(iterator: Union[dict, Iterable]) -> List[str]:
    """Run format_md_list with the default list prefix set to a check or task list format."""  # noqa
    logger.debug('Starting "format_md_task_list": {iterator}', iterator=iterator)
    return format_md_list(iterator, list_prefix='* [ ]')


def find_images(path_source: Path, parents: Iterable[Path] = (DIST_IMG, )) -> List[Path]:
    """Find all images related to the recipe."""  # noqa
    paths_image = []
    for parent in [*parents] + [path_source.parent]:
        pattern = f'{path_source.stem}.*g'
        paths_image.extend([*parent.glob(f'{path_source.parent.name}-{pattern}')])
        paths_image.extend([*parent.glob(pattern)])
    return [path_image for path_image in paths_image if path_image.suffix != '.svg']


def unlink_images(path_json: Path, path_md: Path) -> None:
    """Copy images from first the old output and then from the local directory."""  # noqa
    for path_image in find_images(path_json):
        path_image_new = path_md.parent / f'{path_md.stem}{path_image.suffix}'
        new_is_file = path_image_new.is_file()
        logger.debug('{action} {path_image} > {path_image_new}', action='Unlinking',
                     path_image=path_image, path_image_new=path_image_new)
        if new_is_file:
            path_image_new.unlink()


def copy_images(path_json: Path, path_md: Path) -> None:
    """Copy images from first the old output and then from the local directory."""  # noqa
    for path_image in find_images(path_json):
        path_image_new = path_md.parent / f'{path_md.stem}{path_image.suffix}'
        new_is_file = path_image_new.is_file()
        logger.debug('{action} {path_image} > {path_image_new}', action='Skipping' if new_is_file else 'Copying',
                     path_image=path_image, path_image_new=path_image_new)
        if not new_is_file:
            shutil.copy2(path_image, path_image_new)


def image_md(path_image: Path) -> str:
    """Format the image link as markdown."""  # noqa
    return '\n'.join([
        '<!-- Image -->',
        f'![{path_image.name}](./{path_image.name})' + '{: .image-recipe loading=lazy }',  # noqa: P103
        '<!-- /Image -->',
    ])


def md_from_json(path_md: Path, recipe: dict) -> str:
    """Convert the JSON files to a markdown string for MKDocs."""  # noqa
    title = path_md.stem.replace('_', ' ').title()
    stars = ' '.join([ICON_FA_STAR] * recipe['rating'] + [ICON_FA_STAR_OUT] * (5 - recipe['rating']))
    paths_image = find_images(path_md, parents=[])
    image = image_md(paths_image[0]) if paths_image else f'<!-- TODO: Capture image for {title} -->'  # noqa: T101
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


def main() -> None:
    """Convert all JSON files to markdown."""
    dir_json = CWD / 'database'
    dir_md = CWD / 'docs'

    for path_json in dir_json.glob('*/*.json'):
        sub_dir = path_json.parent.name
        logger.info(f'{sub_dir}||{path_json.stem}')

        path_md = dir_md / sub_dir / f'{path_json.stem}.md'
        (path_md.parent).mkdir(exist_ok=True, parents=True)
        unlink_images(path_json, path_md)  # HACK: In development, clear old images
        copy_images(path_json, path_md)
        recipe_data = json.loads(path_json.read_text())
        path_md.write_text(md_from_json(path_md, recipe_data))


if __name__ == '__main__':
    main()

# TODO: Consider making an aggregate page so that the recipes are easier to find
#   ^ possibly just photos and names for a better TOC
