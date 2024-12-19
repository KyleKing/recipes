"""Format Recipes."""

from dataclasses import dataclass, field
from pathlib import Path

from calcipy.file_search import find_project_files_by_suffix
from calcipy.invoke_helpers import get_doc_subdir, get_project_path
from corallium.log import LOGGER

from ._calcipy_djot.markup_table import format_table
from ._calcipy_djot.markup_writer import write_template_formatted_dj_sections
from ._calcipy_djot.markup_writer._writer import _parse_var_comment

# =====================================================================================
# Shared Functionality


def get_recipes_doc_dir() -> Path:
    """Recipes directory (~2-levels up of `get_doc_subdir()`).

    Returns:
        Path: recipe document directory

    """
    project_path: Path = get_project_path()
    return project_path / 'docs'


def _format_titlecase(raw_title: str | None) -> str:
    """Format string in titlecase replacing underscores with spaces.

    Args:
        raw_title: original string title. Typically the filename stem

    Returns:
        str: formatted string

    """
    return raw_title.replace('_', ' ').strip().title() if raw_title else ''


def _format_stars(rating: int) -> str:
    """Format the star icons.

    Args:
        rating: integer user rating

    Returns:
        str: formatted string icons

    """
    if not rating:
        return '_Not yet rated_'
    return f'{rating} / 5'


def _format_image_dj(name_image: str | None, class_: str) -> str:
    """Return formatted markup to display an image from the same directory.

    Args:
        name_image: optional image name
        class_: CSS class name to assign

    """
    if name_image and name_image.lower() != 'none':
        escaped = name_image.replace('_', '\\_')
        return f'![{escaped}](./{name_image}){{.{class_}}}'
    LOGGER.debug('WARN: No image specified', name_image=name_image)
    return '{% TODO: Capture image %}'


# =====================================================================================
# Utilities for updating djot


def _handle_star_section(line: str, path_dj: Path) -> list[str]:  # noqa: ARG001
    """Format the star rating as djot.

    Args:
        line: first line of the section
        path_dj: Path to the djot file

    Returns:
        List[str]: updated recipe markup

    """
    rating = int(_parse_var_comment(line)['rating'])
    stars = _format_stars(rating)
    return [
        f'{{% [cts] rating={rating}; (User can specify rating on scale of 1-5) %}}\n',
        'Personal rating: ' + stars,
        '\n{% [cte] %}',
    ]


def _parse_rel_file(line: str, path_dj: Path, key: str) -> Path:
    """Parse the filename from the file.

    Args:
        line: first line of the section
        path_dj: Path to the djot file
        key: string key to use in `_parse_var_comment`

    Returns:
        Path: absolute path

    Raises:
        FileNotFoundError: if the file at the specified path does not exist

    """
    filename = _parse_var_comment(line)[key]
    path_file: Path = path_dj.parent / filename
    if filename.lower() != 'none' and not path_file.is_file():
        raise FileNotFoundError(f'Could not locate {path_file} from {path_dj}')  # noqa: EM102
    return path_file


def _handle_image_section(line: str, path_dj: Path) -> list[str]:
    """Format the string section with the specified image name.

    Args:
        line: first line of the section
        path_dj: Path to the djot file

    Returns:
        List[str]: updated recipe markup

    """
    path_image = _parse_rel_file(line, path_dj, 'name_image')
    name_image = path_image.name
    return [
        f'{{% [cts] name_image={name_image}; (User can specify image name) %}}\n',
        _format_image_dj(name_image, class_='image-recipe'),
        '\n{% [cte] %}',
    ]


# =====================================================================================
# Utilities for TOC


@dataclass
class Recipe:
    """Recipe Model."""

    rating: str = ''
    path_image: Path = field(default_factory=Path)


@dataclass
class _TOCRecipes:
    """Store recipe metadata for TOC."""

    sub_dir: Path
    recipes: dict[str, Recipe] = field(default_factory=dict)

    def handle_star(self, line: str, path_dj: Path) -> list[str]:
        """Store the star rating and write.

        Args:
            line: first line of the section
            path_dj: Path to the djot file

        Returns:
            List[str]: empty list

        Raises:
            ValueError: if rating isn't specified

        """
        key = path_dj.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        try:
            recipe.rating = _parse_var_comment(line)['rating']
        except KeyError as exc:
            msg = f"'rating' not found in '{line}' from {path_dj}"
            raise ValueError(msg) from exc
        self.recipes[key] = recipe
        return _handle_star_section(line, path_dj)

    def handle_image(self, line: str, path_dj: Path) -> list[str]:
        """Store image name and write.

        Args:
            line: first line of the section
            path_dj: Path to the djot file

        Returns:
            List[str]: empty list

        Raises:
            ValueError: if image_name isn't specified

        """
        key = path_dj.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        try:
            recipe.path_image = _parse_rel_file(line, path_dj, 'name_image')
        except KeyError as exc:
            msg = f"'name_image' not found in '{line}' from {path_dj}"
            raise ValueError(msg) from exc
        self.recipes[key] = recipe
        return _handle_image_section(line, path_dj)

    def write_toc(self) -> None:
        """Write the table of contents."""
        if self.recipes:
            records = [
                {
                    'Link': f'[{_format_titlecase(path_recipe.stem)}](./{path_recipe.with_suffix(".html").name})',
                    'Rating': int(info.rating),
                    'Image': _format_image_dj(info.path_image.name, class_='image-toc'),
                }
                for path_recipe, info in [(Path(key), value) for key, value in self.recipes.items()]
            ]
            toc_table = format_table(headers=[*records[0]], records=records, delimiters=[':-', '-:', ':-:'])
            text = f'# Table of Contents ({_format_titlecase(self.sub_dir.name)})\n\n{toc_table}\n'
            (self.sub_dir / 'index.dj').write_text(text)


# =====================================================================================
# Main Task


def format_recipes() -> None:
    """Format the Recipes."""
    # Get all sub-directories
    paths_dj = find_project_files_by_suffix(get_project_path()).get('dj') or []
    dj_dirs = {path_dj.parent for path_dj in paths_dj}

    # Filter out any directories from calcipy
    dir_dj = get_recipes_doc_dir()
    doc_dir = get_doc_subdir(get_project_path())
    filtered_dir = [pth for pth in dj_dirs if pth.parent == dir_dj and pth.name != doc_dir.name]

    # Create a TOC for each directory
    for sub_dir in filtered_dir:
        LOGGER.info('Creating TOC', sub_dir=sub_dir)
        toc_recipes = _TOCRecipes(sub_dir=sub_dir)
        recipe_lookup = {
            'rating=': toc_recipes.handle_star,
            'name_image=': toc_recipes.handle_image,
        }
        sub_dir_paths = [pth for pth in paths_dj if pth.is_relative_to(sub_dir)]
        write_template_formatted_dj_sections(handler_lookup=recipe_lookup, paths_dj=sub_dir_paths)  # type: ignore[arg-type]
        toc_recipes.write_toc()
