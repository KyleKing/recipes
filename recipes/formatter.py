"""Format Markdown Files for MKDocs."""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from loguru import logger

# =====================================================================================
# Shared Functionality

CWD = Path(__file__).resolve().parents[1]
DIR_MD = CWD / 'docs'

BUMP_RATING = 3
"""Integer to increase the rating so that the lowest is not 1."""


def _format_titlecase(raw_title: str) -> str:
    """Format string in titlecase replacing underscores with spaces.

    Args:
        raw_title: original string title. Typically the filename stem

    Returns:
        str: formatted string

    """
    return raw_title.replace('_', ' ').strip().title()


def _exclude_toc(paths_md: List[Path]) -> List[Path]:
    """Exclude any TOC files from the list of markdown paths."""  # noqa: DAR101,DAR201
    return [_p for _p in paths_md if '_toc' not in _p.stem.lower()]


def _format_stars(rating: int) -> str:
    """Format the star icons.

    Args:
        rating: integer user rating

    Returns:
        str: formatted string icons

    """
    if rating != 0:
        return ' '.join([_ICON_FA_STAR] * (rating + BUMP_RATING) + [_ICON_FA_STAR_OUT] * (5 - rating))
    return '*Not yet rated*'


def _format_image_md(name_image: Optional[str], attrs: str) -> str:
    """Format the image as markdown.

    Args:
        name_image: string image name or None
        attrs: string space-separated attributes to add

    Returns:
        str: formatted image markdown string

    """
    if name_image and name_image.lower() != 'none':
        return f'![{name_image}](./{name_image}){{: {attrs} loading=lazy }}'
    logger.debug(f'WARN: No image specified: `{name_image}`')
    return '<!-- TODO: Capture image -->'  # noqa: T101


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

    Raises:
        AttributeError: if problem with parsing of the regular expression

    """
    try:
        match = _RE_VAR_COMMENT.match(section.strip()).groupdict()
        return {match['key']: match['value']}
    except AttributeError:
        logger.exception(
            'Error parsing `{section}` with `{_RE_VAR_COMMENT}`', section=section,
            _RE_VAR_COMMENT=_RE_VAR_COMMENT,
        )
        raise


def _format_header(_section: str, path_md: Path) -> str:
    """Format the section header."""  # noqa: DAR101,DAR201
    return '<!-- Do not modify sections with "AUTO-*". They are updated by make.py -->'


def _format_star_section(section: str, path_md: Path) -> str:
    """Format the star rating as markdown.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    """
    rating = int(_parse_var_comment(section)['rating'])
    stars = _format_stars(rating)
    return '\n'.join([
        f'<!-- rating={rating}; (User can specify rating on scale of 1-5) -->',
        '<!-- AUTO-UserRating -->',
        'Personal rating: ' + stars,
        '<!-- /AUTO-UserRating -->',
    ])


def _format_image_section(section: str, path_md: Path) -> str:
    """Format the string section with the specified image name.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    Raises:
        FileNotFoundError: if the image file could not be located

    """
    name_image = _parse_var_comment(section)['name_image']
    path_image = path_md.parent / name_image
    if name_image.lower() != 'none' and not path_image.is_file():
        raise FileNotFoundError(f'Could not locate {path_image} from {path_md}')

    return '\n'.join([
        f'<!-- name_image={name_image}; (User can specify image name) -->',
        '<!-- AUTO-Image -->',
        _format_image_md(name_image, attrs='.image-recipe'),
        '<!-- /AUTO-Image -->',
    ])


def _check_todo(section: str, _path_md: Path) -> str:
    """Pass-through to identify sections that contain a task."""  # noqa:
    logger.warning(f'Found TODO {section}')  # noqa: T101
    return section


def _check_unknown(section: str, _path_md: Path) -> str:  # noqa
    """Pass-through to catch sections not parsed by the function logic."""  # noqa:
    logger.error('Could not parse: {section} from: {path_md}', section=section, path_md=_path_md)
    return section


def _update_md(path_md: Path) -> str:
    """Parse the markdown recipe and replace auto-formatted sections.

    Args:
        path_md: Path to the markdown file

    Returns:
        str: updated recipe string markdown

    """
    startswith_action_lookup: Dict[str, Callable[[str, Path], str]] = {
        '<!-- Do not modify sections with ': _format_header,
        '<!-- rating=': _format_star_section,
        '<!-- name_image=': _format_image_section,
        '<!-- TODO': _check_todo,  # noqa: T101
        '<!-- ': _check_unknown,
    }
    sections = []
    for section in path_md.read_text().split('\n\n'):
        for startswith, action in startswith_action_lookup.items():
            if section.strip().startswith(startswith):
                sections.append(action(section, path_md))
                break
        else:
            sections.append(section)
    return '\n\n'.join(sections)


def _write_auto_gen() -> None:
    """Update auto-generated markdown contents."""
    for path_md in _exclude_toc([*DIR_MD.glob('*/*.md')]):
        logger.info('> {path_md}', path_md=path_md)
        path_md.write_text(_update_md(path_md))


# =====================================================================================
# Utilities for TOC


def _format_toc(toc_data: Dict[str, str]) -> str:
    """Format a single list item for the TOC from parsed data.

    Args:
        toc_data: dictionary of key and data parsed from source file

    Returns:
        str: single TOC item

    """
    link = f"[{_format_titlecase(toc_data['name_md'])}](../{toc_data['name_md']})"
    rating = int(toc_data['rating'])
    # Note: the relative link needs to be ../ to work. Will otherwise try to go to './__TOC/<link>'
    return (
        f'| {link}'
        f' | {rating + BUMP_RATING}'
        f" | {_format_image_md(toc_data['name_image'], attrs='.image-toc')}"
        ' |'
    )


def _create_toc_entry(path_md: Path) -> str:
    """Parse the section and return a single list item for the TOC.

    Args:
        path_md: Path to the markdown file

    Returns:
        str: single TOC item

    """
    startswith_items = [
        '<!-- rating=',
        '<!-- name_image=',
    ]
    toc_data = {'name_md': path_md.stem, 'name_image': None}
    for section in path_md.read_text().split('\n\n'):
        for startswith in startswith_items:
            if section.strip().startswith(startswith):
                logger.debug('Matched `{startswith}` against: {section}', startswith=startswith, section=section)
                toc_data = {**toc_data, **_parse_var_comment(section)}
                break
    logger.debug('{toc_data}', toc_data=toc_data, path_md=path_md)
    return _format_toc(toc_data)


def _write_toc() -> None:
    """Write the table of contents for each section."""
    for dir_sub in DIR_MD.glob('*'):
        if dir_sub.parent.name != 'zdev':  # FYI: Make this configurable
            continue

        toc_table = '| Link | Rating | Image |\n| -- | -- | -- |'
        paths_md = [*dir_sub.glob('*.md')]
        for path_md in _exclude_toc(paths_md):
            toc_table += '\n' + _create_toc_entry(path_md)

        if paths_md:
            toc_text = f'# Table of Contents ({_format_titlecase(dir_sub.name)})\n\n{toc_table}\n'
            (dir_sub / '__TOC.md').write_text(toc_text)


# =====================================================================================


def run() -> None:
    """Format the markdown files."""
    _write_auto_gen()
    _write_toc()
