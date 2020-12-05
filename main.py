"""Convert JSON files to markdown for mkdocs."""

import sys
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stdout, level='INFO')

CWD = Path(__file__).resolve().parent
DIR_MD = CWD / 'docs'

ICON_FA_STAR = ':fontawesome-solid-star:'
ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
ICON_M_STAR = ':material-star:'
ICON_M_STAR_OUT = ':material-star-outline:'
ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'  # noqa: P103
ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'  # noqa: P103


def _format_stars(rating: int) -> str:
    """Format the star rating as markdown."""  # noqa
    return '\n'.join([
        f'<!-- rating={rating}; (User can specify rating on scale of 1-5) -->',
        '<!-- AUTO-UserRating -->',
        'Personal rating: ' + ' '.join([ICON_FA_STAR] * rating + [ICON_FA_STAR_OUT] * (5 - rating)),
        '<!-- /AUTO-UserRating -->',
    ])


def _image_md(path_image: Path) -> str:
    """Format the image link as markdown."""  # noqa
    return '\n'.join([
        '<!-- AUTO-Image -->',
        f'![{path_image.name}](./{path_image.name})' + '{: .image-recipe loading=lazy }',  # noqa: P103
        '<!-- /AUTO-Image -->',
    ])


def _update_md(recipe_md: str) -> str:
    """Parse the markdown recipe and replace auto-formatted sections.

    Args:
        recipe_md: string markdown recipe

    Returns:
        str: updated recipe string markdown

    """
    sections = []
    for section in recipe_md.split('\n\n'):
        if section.startswith('<!-- '):
            logger.warning(section)
        sections.append(section)
    return '\n\n'.join(sections)


def main() -> None:
    """Convert all JSON files to markdown."""
    for path_md in DIR_MD.glob('*/*.md'):
        sub_dir = path_md.parent.name
        logger.info(f'{sub_dir}||{path_md.stem}')
        path_md.write_text(_update_md(path_md.read_text()))

        break


if __name__ == '__main__':
    main()
