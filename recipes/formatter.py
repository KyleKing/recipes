"""Format Markdown Files for MKDocs."""

import re
from pathlib import Path

from loguru import logger

CWD = Path(__file__).resolve().parents[1]
DIR_MD = CWD / 'docs'

# =====================================================================================
# Utilities for updating Markdown

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


def _format_header(_section: str, path_md: Path) -> str:
    """Format the section header."""  # noqa: DAR101,DAR201
    return '<!-- Do not modify sections with "AUTO-*". They are updated by make.py -->'


def _format_stars(section: str, path_md: Path) -> str:
    """Format the star rating as markdown.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    """
    rating = int(_parse_var_comment(section)['rating'])
    # Increase the rating so that the lowest is not 1
    bump_rating = 3
    if rating != 0:
        stars = ' '.join([_ICON_FA_STAR] * (rating + bump_rating) + [_ICON_FA_STAR_OUT] * (5 - rating))
    else:
        stars = '*Not yet rated*'
    # Combine the output markdown
    return '\n'.join([
        f'<!-- rating={rating}; (User can specify rating on scale of 1-5) -->',
        '<!-- AUTO-UserRating -->',
        'Personal rating: ' + stars,
        '<!-- /AUTO-UserRating -->',
    ])


def _format_image_md(section: str, path_md: Path) -> str:
    """Format the string section with the specified image name.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    """
    name_image = _parse_var_comment(section)['name_image']
    path_image = path_md.parent / name_image
    if not path_image.is_file():
        raise FileNotFoundError(f'Could not locate {path_image} from {path_md}')

    return '\n'.join([
        f'<!-- name_image={name_image}; (User can specify image name if multiple exist) -->',
        '<!-- AUTO-Image -->',
        f'![{name_image}](./{name_image})' + '{: .image-recipe loading=lazy }',  # noqa: P103
        '<!-- /AUTO-Image -->',
    ])


def _check_todo(section: str, _path_md: Path) -> str:
    """Pass-through to identify sections that contain a task."""  # noqa:
    logger.warning(f'Found TODO {section}')  # noqa: T101
    return section


def _check_unknown(section: str, _path_md: Path) -> str:  # noqa
    """Pass-through to catch sections not parsed by the function logic."""  # noqa:
    logger.error('Could not parse: {section}', section=section)
    return section


def _update_md(recipe_md: str, path_md: Path) -> str:
    """Parse the markdown recipe and replace auto-formatted sections.

    Args:
        recipe_md: string markdown recipe
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    """
    startswith_lookup = {
        '<!-- Do not modify sections with ': _format_header,
        '<!-- rating=': _format_stars,
        '<!-- name_image=': _format_image_md,
        '<!-- Do not modify sections with ': _format_header,
        '<!-- TODO': _check_todo,  # noqa: T101
        '<!-- ': _check_unknown,
    }
    sections = []
    for section in recipe_md.split('\n\n'):
        for startswith, action in startswith_lookup.items():
            if section.strip().startswith(startswith):
                sections.append(action(section, path_md))
                break
        else:
            sections.append(section)
    return '\n\n'.join(sections)


def _write_auto_gen() -> None:
    """Update auto-generated markdown contents."""
    for path_md in DIR_MD.glob('*/*.md'):
        logger.info('> {path_md}', path_md=path_md)
        path_md.write_text(_update_md(path_md.read_text(), path_md))


def run() -> None:
    """Format the markdown files."""
    _write_auto_gen()
