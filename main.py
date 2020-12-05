"""Convert JSON files to markdown for mkdocs."""

import re
import sys
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stdout, level='INFO')

CWD = Path(__file__).resolve().parent
DIR_MD = CWD / 'docs'

_ICON_FA_STAR = ':fontawesome-solid-star:'
_ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
_ICON_M_STAR = ':material-star:'
_ICON_M_STAR_OUT = ':material-star-outline:'
_ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'  # noqa: P103
_ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'  # noqa: P103

_RE_VAR_COMMENT = re.compile(r'<!-- (?P<key>[^=]+)=(?P<value>[^;]+);')


def _parse_var_comment(section: str) -> str:
    """Parse the HTML variable from an HTML or Markdown comment.

    Examples:
    - `<!-- rating=1; (User can specify rating on scale of 1-5) -->`
    - `<!-- path_image=./docs/imgs/image_filename.png; -->`
    - `<!-- tricky_var_3=-11e-21; -->`

    Args:
        section: string section of a markdown recipe

    Returns:
        str: updated recipe string markdown

    """
    match = _RE_VAR_COMMENT.match(section).groupdict()
    return {match['key']: match['value']}


def _format_header(_section: str) -> str:
    """Format the section header."""  # noqa: DAR101,DAR201
    return '<!-- Do not modify sections with "AUTO-*". They are updated by make.py -->'


def _format_stars(section: str) -> str:
    """Format the star rating as markdown.

    Args:
        section: string section of a markdown recipe

    Returns:
        str: updated recipe string markdown

    """
    rating = int(_parse_var_comment(section)['rating'])
    return '\n'.join([
        f'<!-- rating={rating}; (User can specify rating on scale of 1-5) -->',
        '<!-- AUTO-UserRating -->',
        'Personal rating: ' + ' '.join([_ICON_FA_STAR] * rating + [_ICON_FA_STAR_OUT] * (5 - rating)),
        '<!-- /AUTO-UserRating -->',
    ])


    """Format the string section with the specified image name.

    Args:
        section: string section of a markdown recipe

    Returns:
        str: updated recipe string markdown

    """
    name_image = _parse_var_comment(section)['name_image']
    return '\n'.join([
        f'<!-- name_image={name_image}; (User can specify image name if multiple exist) -->',
        '<!-- AUTO-Image -->',
        f'![{name_image}](./{name_image})' + '{: .image-recipe loading=lazy }',  # noqa: P103
        '<!-- /AUTO-Image -->',
    ])


def _match_todo(section: str) -> str:
    logger.warning(f'Found TODO {section}')  # noqa: T101
    return section


def _check_unknown(section: str) -> str:  # noqa
    """Pass-through to catch sections not parsed by the function logic."""  # noqa:
    logger.error('Could not parse: {section}', section=section)
    return section


def _update_md(recipe_md: str) -> str:
    """Parse the markdown recipe and replace auto-formatted sections.

    Args:
        recipe_md: string markdown recipe

    Returns:
        str: updated recipe string markdown

    """
    startswith_lookup = {
        '<!-- Do not modify sections with ': _format_header,
        '<!-- rating=': _format_stars,
        '<!-- name_image=': _image_md,
        '<!-- Do not modify sections with ': _format_header,
        '<!-- TODO': _match_todo,  # noqa: T101
        '<!-- ': _check_unknown,
    }
    sections = []
    for section in recipe_md.split('\n\n'):
        for startswith, action in startswith_lookup.items():
            if section.strip().startswith(startswith):
                sections.append(action(section))
                break
        else:
            sections.append(section)
    return '\n\n'.join(sections)


def main() -> None:
    """Convert all JSON files to markdown."""
    for path_md in DIR_MD.glob('*/*.md'):
        logger.info(f'{path_md.parent.name}||{path_md.stem}')
        path_md.write_text(_update_md(path_md.read_text()))


# Temporary function to identify duplicates images which may need to be edited
def find_image_duplicates():  # noqa
    for path_md in DIR_MD.glob('*/*.md'):
        paths_image = [*path_md.parent.glob(f'{path_md.stem}.*g')]
        if len(paths_image) > 1:
            logger.info(path_md)


if __name__ == '__main__':
    find_image_duplicates()
    # main()
