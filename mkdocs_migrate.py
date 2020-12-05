"""Convert JSON files to markdown for mkdocs."""

import json
from pathlib import Path
from pprint import pprint

from loguru import logger

ICON_FA_STAR = ':fontawesome-solid-star:'
ICON_FA_STAR_OUT = ':fontawesome-regular-star:'
ICON_M_STAR = ':material-star:'
ICON_M_STAR_OUT = ':material-star-outline:'
ICON_O_STAR = ':octicons-star-fill-24:{: .yellow }'
ICON_O_STAR_OUT = ':octicons-star-24:{: .yellow }'


def image_html(path_image: str) -> str:
    # Should also optimize the image with:
    #   squip_cli = Path.home() / '.nvm/versions/node/v8.10.0/bin/sqip'
    #   logger.debug('Creating placeholder image: {} for {}'.format(outPth, recipe['imgSrc']))
    #   retcode = subprocess.call('{} -o {} {}'.format(squip_cli, outPth, recipe['imgSrc']), shell=True)

    return '\n'.join([
        '<!-- Start:Image (WIP: Placeholder) -->',
        '![recipe-breakfast_burrito](/dist/imgs/breakfast-breakfast_burrito.jpeg){: .image-recipe loading=lazy }'
        '<!-- End:Image (WIP: Placeholder) -->',
    ])


def md_from_json(filename: str, recipe: dict) -> str:
    title = filename.replace('_', ' ').title()
    if recipe['source']:
        title += f"\n\n> Based on [{recipe['source']}]({recipe['source']})"
    stars = ' '.join([ICON_FA_STAR] * recipe['rating'] + [ICON_FA_STAR_OUT] * (5 - recipe['rating']))
    image = image_html('TBD')  # HACK: need to locate the image file, which will be copied for migration
    # ^ also ensure that all images in database/ are copied too
    sections = [
        '<!-- Do not modify. Auto-generated with mkdocs_migrate.py -->',
        f'# {title}',
        'Personal rating: ' + stars,
        image,
        '## Ingredients',  # FIXME: 3-Handle sub-categories of ingredients
        '- [ ] ' + '\n- [ ] '.join(recipe['ingredients']),
        '## Recipe',
        '- ' + '\n- '.join(recipe['recipe']),
    ]
    if recipe['notes']:
        sections.extend([
            '## Notes',
            '- ' + '\n- '.join(recipe['notes']),
        ])
    return '\n\n'.join(sections) + '\n'


if __name__ == '__main__':
    CWD = Path(__file__).resolve().parent
    dir_json = CWD / 'database'
    dir_md = CWD / 'docs'

    for path_json in dir_json.glob('*/*.json'):
        sub_dir = path_json.parent.name
        logger.info(f'{sub_dir}||{path_json.stem}')
        recipe_data = json.loads(path_json.read_text())
        pprint(recipe_data)

        path_md = dir_md / sub_dir / f'{path_json.stem}.md'
        (path_md.parent).mkdir(exist_ok=True, parents=True)
        # TODO: 1-Copy and link the image

        path_md.write_text(md_from_json(path_json.stem, recipe_data))

        break

    # TODO: 2-Test `mkdocs gh-deploy`

# TODO: Consider making an aggregate page so that the recipes are easier to find
#   ^ possibly just photos and names for a better TOC
