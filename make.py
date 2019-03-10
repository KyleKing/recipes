"""Generate JS Database file from source Recipe files (JSON)."""

import json
import logging
import shutil
import subprocess
import sys
from os import path
from pathlib import Path, PurePath

# Debugging Options
debug = True
rmDist = False

lgr_fn = 'recipes.log'
logger = logging.getLogger(__name__)


class SiteCompiler:
    """Build JavaScript database file and compile images for distribution."""

    DIR_DIST = Path.cwd() / 'dist'
    DIR_DIST_IMGS = Path.cwd() / 'dist/imgs'
    DIR_SRC = Path.cwd() / 'database'

    def __init__(self):
        """Initialize class."""
        self.imgs = {}     # dict mapping recipe to image file
        self.recipes = []  # list of all recipes
        self.db_fn = self.DIR_DIST / 'database.json'

        self.make()

    def make(self):
        """Compile dist resources."""
        # Configure output directory structure
        self.create_dir(self.DIR_DIST, rm=rmDist)
        self.create_dir(self.DIR_DIST_IMGS)

        # Copy source images into destination directory
        logger.debug('\n# Copying images from {} to {}'.format(self.DIR_SRC, self.DIR_DIST))
        self.glob_cb(self.DIR_SRC, '*/*', self.cp_imgs)

        # Combine JSON documents into single file
        self.toc = {}
        self.glob_cb(self.DIR_SRC, '*/*.json', self.read_json)
        self.dump_json()
        self.json_to_js()

        # Cleanup files from previous builds
        self.remove_old_files()

    # General utilities

    def create_dir(self, dir_pth, rm=False):
        """General utility for working with directories.

        dir_pth -- path to output directory
        rm -- delete existing directory, if one found

        """
        # Remove the initial directory
        if rm and dir_pth.is_dir():
            shutil.rmtree(dir_pth)
        # Attempt to create a directory if one does not already exist
        if not dir_pth.is_dir():
            dir_pth.mkdir(parents=True)

    def write(self, fn, content, mode='w'):
        """Write to target file.

        fn -- filename
        content -- text to append to file
        mode -- default to overwrite file ('w'). Set to 'a' to append

        """
        with fn.open(mode=mode) as fileHandler:
            fileHandler.write(content)

    def glob_cb(self, pth, pattern, cb):
        """Glob given path and use callback on filename.

        pth -- Path, base filename
        pattern -- glob pattern
        cb -- callback function on matched files

        """
        # Parse filenames and pass to callback. Sort to minimize diff
        for fn_src in sorted(pth.glob(pattern)):
            recipe_title = fn_src.name.split('.')[0]
            sub_dir = self.get_n_parent_dirs(fn_src)
            cb(fn_src, sub_dir, recipe_title, file_type=fn_src.suffix.lower())

    def get_n_parent_dirs(self, pth, count=1):
        """Return the reverse-traversed path for the given parent directories.

        This is the reverse behavior of Path.parents[1]

        pth -- Path object
        count -- Number of directories to traverse

        """
        return path.sep.join(str(pth.parent).split(path.sep)[-count:])

    def get_relative_dir(self, pth):
        """Return the string relative of the provided Path object compared to the cwd.

        pth -- Path object

        """
        return str(pth).replace(str(Path.cwd()), '').strip(path.sep)

    # Image manipulation utilities

    def cp_imgs(self, fn_src, sub_dir, recipe_title, file_type):
        """Check if image exists for given recipe and if so, copy to dist directory.

        fn_src -- Relative source filename
        sub_dir -- String, sub_directory
        recipe_title -- Filename without extension
        file_type -- Lowercase file extension name

        """
        # Only applies to specific types of image files
        if file_type in ['.jpeg', '.jpg', '.png']:
            # Track matched image filenames
            fn_dest = self.format_img_name(sub_dir, recipe_title, file_type)
            self.imgs[recipe_title] = self.get_relative_dir(fn_dest)
            # If the image does not exist of if the source image has been updated, copy to the output location
            lbl = 'NOT'
            if not fn_dest.is_file() or fn_src.stat().st_size != fn_dest.stat().st_size:
                lbl = '> >'
                shutil.copyfile(fn_src, fn_dest)
                # Check if the SVG file exists and needs to be removed and recreated later
                svg_fn = Path(self.format_svg_name(fn_dest))
                if svg_fn.is_file():
                    logger.debug('\tRemoving outdated SVG placeholder: {}'.format(svg_fn))
                    svg_fn.unlink()
            logger.debug('{} Copying `{}` to `{}`'.format(lbl, fn_src, fn_dest))
        elif file_type in ['.json', '']:
            pass  # Note: hidden (./.*) files have an empty filetype
        else:
            logger.debug('WARN: Skipping filetype: {} / {}'.format(file_type, fn_src))

    def format_img_name(self, sub_dir, recipe_title, file_type):
        """Return the image filename based subdirectory and recipe title.

        sub_dir -- String, sub_directory
        recipe_title -- Filename without extension

        """
        return self.DIR_DIST_IMGS / '{}-{}{}'.format(sub_dir, recipe_title, file_type)

    def format_svg_name(self, img_src):
        """Return the SVG filename based on the source image filename.

        img_src -- Path to the image file

        """
        pth = PurePath(img_src)
        return str(pth.parent / 'placeholder_{}.svg'.format(pth.name.split('.')[0]))

    # JSON File utilities

    def read_json(self, fn_src, sub_dir, recipe_title, **kwargs):
        """Read JSON and append to database object.

        fn_src -- Relative source filename
        sub_dir -- Sub_directory
        recipe_title -- Filename without extension
        file_type -- File extensions
        kwargs -- additional keyword arguments

        """
        logger.debug('Reading Recipe: `{}`'.format(fn_src))
        recipe = json.loads(fn_src.read_text())

        # Make sure the minimum keys exist
        min_keys = ('ingredients', 'notes', 'recipe', 'source')
        found_keys = [rcp_key for rcp_key in recipe if rcp_key in min_keys]
        if len(found_keys) != len(min_keys):
            raise AttributeError('Recipe ({}) has: `{}` but needs at least: `{}`'.format(fn_src, found_keys, min_keys))

        # Store sub_directory grouping
        recipe['group'] = sub_dir
        # Add recipe title as title case of filename split on underscores
        recipe['id'] = 'recipe-{}'.format(recipe_title)
        recipe['title'] = recipe_title.replace('_', ' ').title()
        # Extend table of contents
        if (sub_dir not in self.toc):
            self.toc[sub_dir] = []
        self.toc[sub_dir].append('{}:{}:{}'.format(recipe['id'], recipe['title'], recipe['rating']))
        # Adds link to minified image
        if recipe_title in self.imgs:
            recipe['imgSrc'] = self.imgs[recipe_title]
            recipe['imgPlaceholder'] = self.format_svg_name(recipe['imgSrc'])
            outPth = Path(recipe['imgPlaceholder'])
            if not outPth.is_file():
                squip_cli = Path.home() / '.nvm/versions/node/v8.10.0/bin/sqip'
                logger.debug('Creating placeholder image: {} for {}'.format(outPth, recipe['imgSrc']))
                retcode = subprocess.call('{} -o {} {}'.format(squip_cli, outPth, recipe['imgSrc']), shell=True)
                if retcode < 0:
                    logger.debug('Error in subprocess ({})'.format(retcode), file=sys.stderr)
        else:
            recipe['imgSrc'] = ''
            recipe['imgPlaceholder'] = ''
        # Standardizes ingredients (accepts either object of arrays or simply array)
        if type(recipe['ingredients']) is list:
            recipe['ingredients'] = {'ingredients': recipe['ingredients']}
        for header, ingredients in recipe['ingredients'].items():
            # Add header in list, so Fuse can attempt to find a match
            recipe['ingredients'][header] = [header.title()]
            recipe['ingredients'][header].extend([ing.strip().lower() for ing in ingredients])

        # TODO: Catch other errors in source files

        self.recipes.append(recipe)

    def dump_json(self):
        """Export recipes to a single JSON file."""
        logger.debug('\n# Exporting recipes to a single summary file')
        # Get each unique key (section header) for ingredients
        search_keys = ['notes', 'recipe', 'title', 'group']
        for recipe in self.recipes:
            search_keys.extend(['ingredients.{}'.format(hdr) for hdr in recipe['ingredients']])
        search_keys = sorted(list(set(search_keys)))
        logger.debug('search_keys: {}'.format(search_keys))
        # Write JSON file (FYI: Camel-case variables for JS output)
        rcps_obj = {'recipes': self.recipes, 'searchKeys': search_keys, 'toc': self.toc}
        kwargs = {'indent': 0, 'separators': (',', ': ')} if debug else {'separators': (',', ':')}
        json.dump(rcps_obj, self.db_fn.open(mode='w'), sort_keys=True, **kwargs)

    def json_to_js(self):
        """Reformat JSON file as JS with variable declaration, so file can be loaded without Cross-Origin Errors."""
        self.write(Path(str(self.db_fn)[:-2]), 'var localDB = {}'.format(self.db_fn.read_text()))

    def remove_old_files(self):
        """Remove any image files no longer linked to source data."""
        logger.debug('\n# Checking if any files need to be removed')
        images = [_fn for _fn in self.imgs.values()]
        images.extend([self.format_svg_name(_fn) for _fn in images])  # Add SVG filenames
        for img_fn in self.DIR_DIST_IMGS.glob('*'):
            if self.get_relative_dir(img_fn) not in images:
                logger.debug('Removing unused image file: {}'.format(img_fn))
                Path(img_fn).unlink()


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(lgr_fn, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s %(filename)s:%(lineno)d\t%(message)s'))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)

    logger.debug('Running with options: debug:{} / rmDist:{}'.format(debug, rmDist))
    SiteCompiler()
