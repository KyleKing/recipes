"""Format Markdown Files for MKDocs."""
from collections import defaultdict
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from beartype import beartype
from calcipy.doit_tasks.doc import _parse_var_comment, _ReplacementMachine, write_autoformatted_md_sections
from calcipy.doit_tasks.doit_globals import DG
from calcipy.file_helpers import get_doc_dir, read_lines
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


@beartype
@contextmanager
def _configure_recipe_lookup(new_lookup: dict[str, Callable[[str, Path], str]]):
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
def _handle_star_section(line: str, path_md: Path) -> list[str]:
    """Format the star rating as markdown.

    Args:
        line: first line of the section
        path_md: Path to the markdown file

    Returns:
        List[str]: updated recipe string markdown

    """
    rating = int(_parse_var_comment(line)['rating'])
    stars = _format_stars(rating)
    return [
        f'<!-- {{cts}} rating={rating}; (User can specify rating on scale of 1-5) -->\n',
        'Personal rating: ' + stars,
        '\n<!-- {cte} -->',
    ]


@beartype
def _parse_rel_file(line: str, path_md: Path, key: str) -> Path:
    """Parse the filename from the file.

    Args:
        line: first line of the section
        path_md: Path to the markdown file
        key: string key to use in `_parse_var_comment`

    Returns:
        Path: absolute path

    Raises:
        FileNotFoundError: if the file at the specified path does not exist

    """
    filename = _parse_var_comment(line)[key]
    path_file = path_md.parent / filename
    if filename.lower() != 'none' and not path_file.is_file():
        raise FileNotFoundError(f'Could not locate {path_file} from {path_md}')
    return path_file


@beartype
def _handle_image_section(line: str, path_md: Path) -> list[str]:
    """Format the string section with the specified image name.

    Args:
        line: first line of the section
        path_md: Path to the markdown file

    Returns:
        List[str]: updated recipe string markdown

    """
    path_image = _parse_rel_file(line, path_md, 'name_image')
    name_image = path_image.name
    return [
        f'<!-- {{cts}} name_image={name_image}; (User can specify image name) -->\n',
        _format_image_md(name_image, attrs='.image-recipe'),
        '\n<!-- {cte} -->',
    ]


# =====================================================================================
# Utilities for TOC


@beartype
def _format_toc_table(toc_records: list[dict[str, Union[str, int]]]) -> list[str]:
    """Format TOC data as a markdown table.

    Args:
        toc_records: list of records

    Returns:
        List[str]: the datatable as a list of lines

    """
    # Format table for Github Markdown
    df_toc = pd.DataFrame(toc_records)
    return df_toc.to_markdown(index=False).split('\n')


@beartype
def _create_toc_record(
    path_recipe: Path, path_img: Path, rating: Union[str, int],
) -> dict[str, Union[str, int]]:
    """Create the dictionary summarizing data for the table of contents.

    Args:
        path_recipe: Path to the recipe
        path_img: Path to the recipe image
        rating: recipe user-rating

    Returns:
        Dict[str, Union[str, int]]: single records

    """
    link = f'[{_format_titlecase(path_recipe.stem)}](./{path_recipe.name})'
    img_md = _format_image_md(path_img.name, attrs='.image-toc')
    return {
        'Link': link,
        'Rating': int(rating) + BUMP_RATING,
        'Image': img_md,
    }


# TODO: Convert to attributes class
class _TOCRecipes:  # noqa: H601
    """Store recipe metadata for TOC."""

    @beartype
    def __init__(self, sub_dir: Path) -> None:
        self.sub_dir = sub_dir
        self.recipes = defaultdict(dict)

    @beartype
    def store_star(self, line: str, path_md: Path) -> list[str]:
        """Store the star rating.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        """
        self.recipes[path_md.as_posix()]['rating'] = _parse_var_comment(line)['rating']
        return []

    @beartype
    def store_image(self, line: str, path_md: Path) -> list[str]:
        """Store image name.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        """
        path_image = _parse_rel_file(line, path_md, 'name_image')
        self.recipes[path_md.as_posix()]['path_image'] = path_image

        return []

    @beartype
    def write_toc(self) -> None:
        """Write the table of contents."""
        if self.recipes:
            records = [
                _create_toc_record(Path(path_md), info['path_image'], info['rating'])
                for path_md, info in self.recipes.items()
            ]
            toc_table = _format_toc_table(records)
            header = [f'# Table of Contents ({_format_titlecase(self.sub_dir.name)})']
            (self.sub_dir / '__TOC.md').write_text('\n'.join(header + [''] + toc_table + ['']))


@beartype
def _write_toc() -> None:
    """Write the table of contents for each section."""
    # Get all subdirectories
    md_dirs = {path_md.parent for path_md in DG.doc.paths_md}

    # Filter out any directories for calcipy that are not recipes
    doc_dir = get_doc_dir(DG.meta.path_project)
    filtered_dir = [pth for pth in md_dirs if pth.parent == DIR_MD and pth.name not in [doc_dir.name]]

    # Create a TOC for each directory
    for sub_dir in filtered_dir:
        logger.info(f'Creating TOC for: {sub_dir}')
        toc_recipes = _TOCRecipes(sub_dir)
        recipe_lookup = {
            'rating=': toc_recipes.store_star,
            'name_image=': toc_recipes.store_image,
        }
        sub_dir_paths = [pth for pth in DG.doc.paths_md if pth.is_relative_to(sub_dir)]
        with _configure_recipe_lookup(recipe_lookup):
            for path_md in sub_dir_paths:
                _ReplacementMachine().parse(read_lines(path_md), DG.doc.handler_lookup, path_md)
        toc_recipes.write_toc()


# =====================================================================================
# Main Task


@beartype
def format_recipes() -> None:
    """Format the markdown files."""
    recipe_lookup = {
        'rating=': _handle_star_section,
        'name_image=': _handle_image_section,
    }
    with _configure_recipe_lookup(recipe_lookup):
        write_autoformatted_md_sections()

    _write_toc()
