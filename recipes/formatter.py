"""Format Markdown Files for MKDocs."""

from dataclasses import dataclass, field
from pathlib import Path

from calcipy.file_search import find_project_files_by_suffix
from calcipy.invoke_helpers import get_doc_subdir, get_project_path
from calcipy.markdown_table import format_table
from calcipy.md_writer import write_template_formatted_md_sections
from calcipy.md_writer._writer import _parse_var_comment  # noqa: PLC2701
from corallium.log import LOGGER

# =====================================================================================
# Shared Functionality


def get_recipes_doc_dir() -> Path:
    """Markdown directory (~2-levels up of `get_doc_subdir()`).

    Returns:
        Path: recipe document directory

    """
    project_path: Path = get_project_path()
    return project_path / 'docs'


_ICON_FA_STAR = ':fontawesome-solid-star:'
"""Font Awesome Star Icon."""

_ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
"""Font Awesome *Outlined* Star Icon."""

# Alternatives to the Font-Awesome star icons
# > _ICON_M_STAR = ':material-star:'
# > _ICON_M_STAR_OUT = ':material-star-outline:'
# > _ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'
# > _ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'


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
        return '*Not yet rated*'
    return ' '.join([_ICON_FA_STAR] * rating + [_ICON_FA_STAR_OUT] * (5 - rating))


def _format_image_md(name_image: str | None, attrs: str) -> str:
    """Format the image as markdown.

    Args:
        name_image: string image name or None
        attrs: string space-separated attributes to add

    Returns:
        str: formatted image markdown string

    """
    if name_image and name_image.lower() != 'none':
        return f'![{name_image}](./{name_image}){{: {attrs} loading=lazy }}'
    LOGGER.debug('WARN: No image specified', name_image=name_image)
    return '<!-- TODO: Capture image -->'


# =====================================================================================
# Utilities for updating Markdown


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

    def handle_star(self, line: str, path_md: Path) -> list[str]:
        """Store the star rating and write.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        Raises:
            ValueError: if rating isn't specified

        """
        key = path_md.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        try:
            recipe.rating = _parse_var_comment(line)['rating']
        except KeyError as exc:
            msg = f"'rating' not found in '{line}' from {path_md}"
            raise ValueError(msg) from exc
        self.recipes[key] = recipe
        return _handle_star_section(line, path_md)

    def handle_image(self, line: str, path_md: Path) -> list[str]:
        """Store image name and write.

        Args:
            line: first line of the section
            path_md: Path to the markdown file

        Returns:
            List[str]: empty list

        Raises:
            ValueError: if image_name isn't specified

        """
        key = path_md.as_posix()
        recipe = self.recipes.get(key) or Recipe()
        try:
            recipe.path_image = _parse_rel_file(line, path_md, 'name_image')
        except KeyError as exc:
            msg = f"'name_image' not found in '{line}' from {path_md}"
            raise ValueError(msg) from exc
        self.recipes[key] = recipe
        return _handle_image_section(line, path_md)

    def write_toc(self) -> None:
        """Write the table of contents."""
        if self.recipes:
            records = [
                {
                    'Link': f'[{_format_titlecase(path_recipe.stem)}](./{path_recipe.name})',
                    'Rating': int(info.rating),
                    'Image': _format_image_md(info.path_image.name, attrs='.image-toc'),
                }
                for path_recipe, info in [(Path(key), value) for key, value in self.recipes.items()]
            ]
            toc_table = format_table(headers=[*records[0]], records=records, delimiters=[':-', '-:', ':-'])
            text = f'# Table of Contents ({_format_titlecase(self.sub_dir.name)})\n\n{toc_table}\n'
            (self.sub_dir / '__TOC.md').write_text(text)


# =====================================================================================
# Main Task


def format_recipes() -> None:
    """Format the Recipes."""
    # Get all sub-directories
    paths_md = find_project_files_by_suffix(get_project_path()).get('md') or []
    md_dirs = {path_md.parent for path_md in paths_md}

    # Filter out any directories from calcipy
    dir_md = get_recipes_doc_dir()
    doc_dir = get_doc_subdir(get_project_path())
    filtered_dir = [pth for pth in md_dirs if pth.parent == dir_md and pth.name != doc_dir.name]

    # Create a TOC for each directory
    for sub_dir in filtered_dir:
        LOGGER.info('Creating TOC', sub_dir=sub_dir)
        toc_recipes = _TOCRecipes(sub_dir=sub_dir)
        recipe_lookup = {
            'rating=': toc_recipes.handle_star,
            'name_image=': toc_recipes.handle_image,
        }
        sub_dir_paths = [pth for pth in paths_md if pth.is_relative_to(sub_dir)]
        write_template_formatted_md_sections(handler_lookup=recipe_lookup, paths_md=sub_dir_paths)  # type: ignore[arg-type]
        toc_recipes.write_toc()
