"""Format Markdown Files for MKDocs."""

from pathlib import Path

import pandas as pd
from beartype import beartype
from beartype.typing import Optional, Union
from calcipy.file_search import find_project_files_by_suffix
from calcipy.invoke_helpers import get_doc_subdir, get_project_path
from calcipy.md_writer import write_autoformatted_md_sections
from calcipy.md_writer._writer import _parse_var_comment
from corallium.log import logger
from pydantic import BaseModel, Field

# =====================================================================================
# Shared Functionality


@beartype
def get_recipes_doc_dir() -> Path:
    """Markdown directory (~2-levels up of `get_doc_subdir()`)."""
    project_path: Path = get_project_path()
    return project_path / 'docs'


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
    logger.debug('WARN: No image specified', name_image=name_image)
    return '<!-- TODO: Capture image -->'  # noqa: T101


# =====================================================================================
# Utilities for updating Markdown


@beartype
def _handle_star_section(line: str, path_md: Path) -> list[str]:  # noqa: ARG001
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
    path_file: Path = path_md.parent / filename
    if filename.lower() != 'none' and not path_file.is_file():
        raise FileNotFoundError(f'Could not locate {path_file} from {path_md}')  # noqa: EM102
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

TOCRecordT = dict[str, Union[str, int]]
"""TOC Record."""


@beartype
def _format_toc_table(toc_records: list[TOCRecordT]) -> list[str]:
    """Format TOC data as a markdown table.

    Args:
        toc_records: list of records

    Returns:
        List[str]: the datatable as a list of lines

    """
    # Format table for Github Markdown
    df_toc = pd.DataFrame(toc_records)
    content = df_toc.to_markdown(index=False)
    assert content is not None  # noqa: S101 for pyright
    return [*content.split('\n')]  # for mypy


@beartype
def _create_toc_record(
    path_recipe: Path, path_img: Path, rating: Union[str, int],
) -> TOCRecordT:
    """Create the dictionary summarizing data for the table of contents.

    Args:
        path_recipe: Path to the recipe
        path_img: Path to the recipe image
        rating: recipe user-rating

    Returns:
        TOCRecordT: single records

    """
    link = f'[{_format_titlecase(path_recipe.stem)}](./{path_recipe.name})'
    img_md = _format_image_md(path_img.name, attrs='.image-toc')
    return {
        'Link': link,
        'Rating': int(rating) + BUMP_RATING,
        'Image': img_md,
    }


class Recipe(BaseModel):
    """Recipe Model."""

    rating: str = ''
    path_image: Path = Path()


class _TOCRecipes(BaseModel):  # noqa: H601
    """Store recipe metadata for TOC."""

    sub_dir: Path
    recipes: dict[str, Recipe] = Field(default_factory=dict)

    @beartype
    def handle_star(self, line: str, path_md: Path) -> list[str]:
        """Store the star rating and write.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        """
        key = path_md.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        recipe.rating = _parse_var_comment(line)['rating']
        self.recipes[key] = recipe
        return _handle_star_section(line, path_md)

    @beartype
    def handle_image(self, line: str, path_md: Path) -> list[str]:
        """Store image name and write.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        """
        key = path_md.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        recipe.path_image = _parse_rel_file(line, path_md, 'name_image')
        self.recipes[key] = recipe
        return _handle_image_section(line, path_md)

    @beartype
    def write_toc(self) -> None:
        """Write the table of contents."""
        if self.recipes:
            records = [
                _create_toc_record(Path(path_md), info.path_image, info.rating)
                for path_md, info in self.recipes.items()
            ]
            toc_table = _format_toc_table(records)
            header = [f'# Table of Contents ({_format_titlecase(self.sub_dir.name)})']
            (self.sub_dir / '__TOC.md').write_text('\n'.join([*header, '', *toc_table] + ['']))


# =====================================================================================
# Main Task


@beartype
def format_recipes() -> None:
    """Format the Recipes."""
    # Get all sub-directories
    paths_md = find_project_files_by_suffix(get_project_path()).get('md') or []
    md_dirs = {path_md.parent for path_md in paths_md}

    # Filter out any directories from calcipy
    dir_md = get_recipes_doc_dir()
    doc_dir = get_doc_subdir(get_project_path())
    filtered_dir = [pth for pth in md_dirs if pth.parent == dir_md and pth.name not in [doc_dir.name]]

    # Create a TOC for each directory
    for sub_dir in filtered_dir:
        logger.info('Creating TOC', sub_dir=sub_dir)
        toc_recipes = _TOCRecipes(sub_dir=sub_dir)
        recipe_lookup = {
            'rating=': toc_recipes.handle_star,
            'name_image=': toc_recipes.handle_image,
        }
        sub_dir_paths = [pth for pth in paths_md if pth.is_relative_to(sub_dir)]
        write_autoformatted_md_sections(handler_lookup=recipe_lookup, paths_md=sub_dir_paths)
        toc_recipes.write_toc()
