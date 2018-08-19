"""Generate JSON Database from Source JSON Files."""

import glob
import json
import logging
import os
import shutil

debug = True
# debug = False

logger = logging.getLogger(__name__)
lgr_fn = 'recipes.log'
formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)d\t%(message)s')

logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(lgr_fn)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


def lgr(msg):
    """General Logger Function."""
    global logger, debug
    if debug:
        print msg
    logger.debug(msg)


class SiteCompiler(object):
    """Build recipe source files for distribution."""

    dist_dir = 'dist/'
    dist_imgs = 'dist/imgs/'
    src_dir = 'database/'

    def __init__(self):
        """Initialize class."""
        self.imgs = {}     # dict mapping recipe to image file
        self.recipes = []  # list of all recipes
        self.db_fn = '{}database.json'.format(self.dist_dir)

        self.make()

    def make(self):
        """Compile dist resources."""
        # Configure output directory structure
        self.create_dir(self.dist_dir, rm=True)
        self.create_dir(self.dist_imgs)

        # Copy source images into destination directory
        self.glob_cb('{}/*/*'.format(self.src_dir), self.cp_imgs)

        # Combine JSON documents into single file
        self.toc = {}
        self.glob_cb('{}/*/*.json'.format(self.src_dir), self.read_json)
        self.dump_json()
        self.json_to_js()

    # General utilities

    def create_dir(self, dir_pth, rm=False):
        """General utility for working with directories.

        dir_pth -- path to output directory
        rm -- delete existing directory, if one found

        """
        # Remove the initial directory
        if rm and os.path.isdir(dir_pth):
            shutil.rmtree(dir_pth)
        # Attempt to create a directory if one does not already exist
        if not os.path.isdir(dir_pth):
            os.makedirs(dir_pth)

    def read(self, fn, split=False):
        """Return the contents of a file.

        fn -- filename
        split -- split raw text on newline

        """
        with open(fn) as fn_:
            contents = fn_.read()
        return contents.split('\n') if split else contents

    def write(self, fn, content):
        """Append to target file.

        fn -- filename
        content -- text to append to file

        """
        with open(fn, 'a') as fn_:
            fn_.write(content)

    def glob_cb(self, pattern, cb):
        """Glob given path and use callback on filename.

        pattern -- glob pattern
        cb -- callback function on globbed files

        """
        # Sort filenames alphabetically
        for fn_src in sorted(glob.glob(pattern)):
            # Split *relative* filename to check file type and path
            dot_split = fn_src.split('.')
            path_split = dot_split[0].split('/')
            if len(dot_split) == 2 and len(path_split) == 3:
                # Pass known path components to callback
                file_type = dot_split[1].lower()
                ___, subdir, recipe_title = path_split
                cb(fn_src, subdir, recipe_title, file_type=file_type)
            else:
                lgr('Unparseable fn: `{}`'.format(fn_src))

    # Image manipulation utilities

    def cp_imgs(self, fn_src, subdir, recipe_title, file_type):
        """Check if image exists for given recipe and if so, copy to dist directory.

        fn_src -- Relative source filename
        subdir -- Subdirectory
        recipe_title -- Filename without extension
        file_type -- File extensions

        """
        # Only applies image files (non-JSON)
        if file_type != 'json':
            # Create destination filename
            fn_dest = '{}{}-{}.{}'.format(self.dist_imgs, subdir, recipe_title, file_type)
            # Track matched image filenames
            self.imgs[recipe_title] = fn_dest
            lgr('Copying `{}` to `{}`'.format(fn_src, fn_dest))
            shutil.copyfile(fn_src, fn_dest)

    # JSON File utilities

    def read_json(self, fn_src, subdir, recipe_title, **kwargs):
        """Read JSON and append to database object.

        fn_src -- Relative source filename
        subdir -- Subdirectory
        recipe_title -- Filename without extension
        file_type -- File extensions
        kwargs -- additional keyword arguments

        """
        lgr('Reading JSON file: `{}`'.format(fn_src))
        with open(fn_src) as fn:
            recipe = json.load(fn)

        # Make sure the minimum keys exist
        min_keys = ('ingredients', 'notes', 'recipe', 'source')
        found_keys = [rcpKey for rcpKey in recipe.iterkeys() if rcpKey in min_keys]
        if len(found_keys) != len(min_keys):
            raise AttributeError('Recipe ({}) has: `{}` but needs at least: `{}`'.format(fn_src, found_keys, min_keys))

        # Store subdirectory grouping
        recipe['group'] = subdir
        # Add recipe title as title case of filename split on underscores
        recipe['id'] = 'recipe-{}'.format(recipe_title)
        recipe['title'] = recipe_title.replace('_', ' ').title()
        # Extend table of contents
        if (subdir not in self.toc):
            self.toc[subdir] = []
        self.toc[subdir].append(recipe['title'])
        # Adds link to minified image
        recipe['imgSrc'] = self.imgs[recipe_title] if recipe_title in self.imgs else ''
        # Standardizes ingredients (accepts either object of arrays or simply array)
        if type(recipe['ingredients']) is list:
            recipe['ingredients'] = {'ingredients': recipe['ingredients']}
        for header, ingredients in recipe['ingredients'].iteritems():
            # Add header in list, so Fuse can attempt to find a match
            recipe['ingredients'][header] = [header.title()]
            recipe['ingredients'][header].extend([ing.strip().lower() for ing in ingredients])

        # TODO: Catch other errors in source files

        self.recipes.append(recipe)

    def dump_json(self):
        """Export recipes to a single JSON file."""
        # Add all unique object keys for Fuse to search
        search_keys = ['notes', 'recipe', 'title', 'group']
        # Get each unique key (section header) for ingredients
        for recipe in self.recipes:
            search_keys.extend(['ingredients.{}'.format(hdr) for hdr in recipe['ingredients'].iterkeys()])
        search_keys = list(set(search_keys))
        lgr('search_keys: {}'.format(search_keys))
        # Write JSON file
        rcps_obj = {'recipes': self.recipes, 'search_keys': search_keys, 'toc': self.toc}
        kwargs = {'separators': (',', ':')} if not debug else {'indent': 4, 'separators': (',', ': ')}
        json.dump(rcps_obj, open(self.db_fn, 'w'), sort_keys=True, **kwargs)

    def json_to_js(self):
        """Add variable declaration so JavaScript can load JSON w/o Cross-Origin Errors for accessing file://."""
        recipes = self.read(self.db_fn)
        self.write(self.db_fn[:-2], 'var localDB = {}'.format(recipes))


if __name__ == '__main__':
    open(lgr_fn, 'w').close()
    SiteCompiler()
