import glob
import logging
import os
import shutil
import json

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
    global logger, debug
    if debug:
        print msg
    logger.debug(msg)


class site_compiler(object):
    """Build recipe source files for distribution"""

    dist_dir = 'dist/'
    dist_imgs = 'dist/imgs/'
    src_dir = 'database/'

    def __init__(self):
        """Initialize class"""
        self.imgs = {}     # dict mapping recipe to image file
        self.recipes = []  # list of all recipes
        self.db_fn = '{}database.json'.format(self.dist_dir)

        self.make()

    def make(self):
        """Compile dist resources"""
        # Configure output directory structure
        self.create_dir(self.dist_dir, rm=True)
        self.create_dir(self.dist_imgs)

        # Copy source images into destination directory
        self.glob_cb('{}/*/*'.format(self.src_dir), self.cp_imgs)

        # Combine JSON documents into single file
        self.glob_cb('{}/*/*.json'.format(self.src_dir), self.read_json)
        self.dump_json()
        self.json_to_js()

    # General utilities

    def create_dir(self, dir_pth, rm=False):
        """General utility for working with directories"""
        # Remove the initial directory
        if rm and os.path.isdir(dir_pth):
            shutil.rmtree(dir_pth)
        # Attempt to create a directory if one does not already exist
        if not os.path.isdir(dir_pth):
            os.makedirs(dir_pth)

    def read(self, fn, split=False):
        """Return the contents of a file"""
        with open(fn) as fn_:
            contents = fn_.read()
        return contents.split('\n') if split else contents

    def write(self, content, fn):
        """Append to target file"""
        with open(fn, 'a') as fn_:
            fn_.write(content)

    def glob_cb(self, pattern, cb):
        """Glob given path and use callback on filename"""
        for fn_src in glob.glob(pattern):
            dot_split = fn_src.split('.')
            path_split = dot_split[0].split('/')
            if len(dot_split) == 2 and len(path_split) == 3:
                file_type = dot_split[1].lower()
                ___, subdir, recipe_title = path_split
                cb(fn_src, subdir, recipe_title, file_type=file_type)
            else:
                lgr('Unparseable fn: `{}`'.format(fn_src))

    # Image manipulation utilities

    def cp_imgs(self, fn_src, subdir, recipe_title, file_type):
        """Copy images from source location to destination directory"""
        if file_type != 'json':
            fn_dest = '{}{}-{}.{}'.format(self.dist_imgs, subdir, recipe_title, file_type)
            self.imgs[recipe_title] = fn_dest
            lgr('Copying `{}` to `{}`'.format(fn_src, fn_dest))
            shutil.copyfile(fn_src, fn_dest)

    # JSON File utilities

    def read_json(self, fn_src, subdir, recipe_title, **kwargs):
        """Read JSON and append to database object"""
        lgr('Reading JSON file: `{}`'.format(fn_src))
        with open(fn_src) as fn:
            recipe = json.load(fn)
        # Store subdirectory grouping
        recipe['group'] = subdir
        # Add recipe title as title case of filename split on underscores
        recipe['title'] = recipe_title.replace('_', ' ').title()
        # Adds link to minified image
        recipe['img_src'] = self.imgs[recipe_title] if recipe_title in self.imgs else ''
        # Standardizes ingredients (accepts either object of arrays or simply array)
        if type(recipe['ingredients']) is list:
            recipe['ingredients'] = {'ingredients': recipe['ingredients']}
        for header, ingredients in recipe['ingredients'].iteritems():
            recipe['ingredients'][header] = [ing.strip().lower() for ing in ingredients]
        # TODO: Identifies errors in source file

        self.recipes.append(recipe)

    def dump_json(self):
        """Export the JSON file"""
        kwargs = {'separators': (',', ':')} if not debug else {'indent': 4}
        rcps_obj = {'recipes': self.recipes}  # wrap array in object
        json.dump(rcps_obj, open(self.db_fn, 'w'), sort_keys=True, **kwargs)

    def json_to_js(self):
        """Add variable declaration so JavaScript can load JSON w/o Cross-Origin Errors for accessing file://"""
        recipes = self.read(self.db_fn)
        self.write('var localDB = {}'.format(recipes), self.db_fn[:-2])


if __name__ == '__main__':
    open(lgr_fn, 'w').close()
    site_compiler()
