"""Format Markdown Files for MKDocs."""

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Optional

from beartype import beartype
from calcipy.doit_tasks.doc import _parse_var_comment, write_autoformatted_md_sections
from calcipy.doit_tasks.doit_globals import DG
from calcipy.file_helpers import get_doc_dir
from decorator import contextmanager
from loguru import logger

# =====================================================================================
# Shared Functionality

DIR_MD = DG.meta.path_project / 'docs'
"""Markdown directory (~2-levels up of `DG.doc.doc_sub_dir`)."""

BUMP_RATING = 3
"""Integer to increase the rating so that the lowest is not 1."""

_ICON_FA_STAR = ':fontawesome-solid-star:'
"""Font Awesome Star Icon."""

_ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
"""Font Awesome *Outlined* Star Icon."""

# Alternatives to the Font-Awesome star icons
# > _ICON_M_STAR = ':material-star:'
# > _ICON_M_STAR_OUT = ':material-star-outline:'
# > _ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'  # noqa: P103
# > _ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'  # noqa: P103


@beartype
def _format_titlecase(raw_title: Optional[str]) -> str:
    """Format string in titlecase replacing underscores with spaces.

    Args:
        raw_title: original string title. Typically the filename stem

    Returns:
        str: formatted string

    """
    return raw_title.replace('_', ' ').strip().title() if raw_title else ''


@beartype
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


@beartype
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


@contextmanager
def _configure_recipe_lookup(new_lookup: dict[str, Callable[[str, Path], str]]) -> None:
    """Configure the handler lookup for recipe tasks.

    Args:
        new_lookup: new handler_lookup to use temporarily

    Yields:
        None

    """
    original_lookup = deepcopy(DG.doc.handler_lookup)
    DG.doc.handler_lookup = new_lookup
    yield
    DG.doc.handler_lookup = original_lookup


# =====================================================================================
# Utilities for updating Markdown


@beartype
def _format_star_section(section: str, path_md: Path) -> list[str]:
    """Format the star rating as markdown.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        list[str]: updated recipe string markdown

    """
    rating = int(_parse_var_comment(section)['rating'])
    stars = _format_stars(rating)
    return [
        f'<!-- {{cts}} rating={rating}; (User can specify rating on scale of 1-5) -->',
        'Personal rating: ' + stars,
        '<!-- {cte} -->',
    ]


@beartype
def _format_image_section(section: str, path_md: Path) -> list[str]:
    """Format the string section with the specified image name.

    Args:
        section: string section of a markdown recipe
        path_md: Path to the markdown file

    Returns:
        list[str]: updated recipe string markdown

    Raises:
        FileNotFoundError: if the image file could not be located

    """
    name_image = _parse_var_comment(section)['name_image']
    path_image = path_md.parent / name_image
    if name_image.lower() != 'none' and not path_image.is_file():
        raise FileNotFoundError(f'Could not locate {path_image} from {path_md}')

    return [
        f'<!-- {{cts}} name_image={name_image}; (User can specify image name) -->',
        _format_image_md(name_image, attrs='.image-recipe'),
        '<!-- {cte} -->',
    ]


# =====================================================================================
# Utilities for TOC


@beartype
def _format_toc(toc_data: dict[str, Optional[str]]) -> str:
    """Format a single list item for the TOC from parsed data.

    Args:
        toc_data: dictionary of key and data parsed from source file

    Returns:
        str: single TOC item

    """
    link = f"[{_format_titlecase(toc_data['name_md'])}](../{toc_data['name_md']})"
    rating = int(str(toc_data['rating']))
    # Note: the relative link needs to be ../ to work. Will otherwise try to go to './__TOC/<link>'
    img_md = _format_image_md(toc_data['name_image'], attrs='.image-toc')
    return f'| {link} | {rating + BUMP_RATING} | {img_md} |'


@beartype
def _create_toc_entry(path_md: Path) -> str:
    """Parse the section and return a single list item for the TOC.

    Args:
        path_md: Path to the markdown file

    Returns:
        str: single TOC item

    """
    startswith_items = [
        '<!-- {cts} rating=',
        '<!-- {cts} name_image=',
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


@beartype
def _write_toc() -> None:
    """Write the table of contents for each section."""
    # FIXME: Use _ReplacementMachine instead of _create_toc_entry
    # logger.info('> {paths_md}', paths_md=DG.doc.paths_md)
    # for path_md in DG.doc.paths_md:
    #     TODO: Use class for DG.doc.handler_lookup to capture metadata of interest
    #     _ReplacementMachine().parse(read_lines(path_md), DG.doc.handler_lookup, path_md)

    doc_dir = get_doc_dir(DG.meta.path_project)
    for dir_sub in DIR_MD.glob('*'):
        if dir_sub.name == doc_dir.name:
            continue  # Don't write a Table of Contents for developer documentation

        toc_table = '| Link | Rating | Image |\n| -- | -- | -- |'
        paths_md = [*dir_sub.glob('*.md')]
        for path_md in DG.doc.path_md:
            toc_table += '\n' + _create_toc_entry(path_md)

        if paths_md:
            toc_text = f'# Table of Contents ({_format_titlecase(dir_sub.name)})\n\n{toc_table}\n'
            (dir_sub / '__TOC.md').write_text(toc_text)


# =====================================================================================
# Main Task


@beartype
def format_recipes() -> None:
    """Format the markdown files."""
    recipe_lookup = {
        'rating=': _format_star_section,
        'name_image=': _format_image_section,
    }
    with _configure_recipe_lookup(recipe_lookup):
        write_autoformatted_md_sections()

    # FIXME: Implement
    # _write_toc()
