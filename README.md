# Recipes

Create interactive website for searching and making lists from user-specified source files

## Workflow

1. Create <recipe_title>.json <recipe_title>.<img_format> in respective database directory. See template for all options.
2. Run `python make.py`
    - Move source images to `dist/imgs/<subdir>-<recipe_title>.<img_format>`
    - Combine JSON documents into single JSON file
        + Add recipe title as title case of filename split on underscores
        + Adds link to minified image
        + Standardizes ingredients
        + Identifies errors in source file
3. Open index.html in a browser or push to Github and view at https://kyleking.me/recipes/

## Libraries

- Crel for DOM creation: https://github.com/KoryNunn/crel
- Fuse for fuzzy-search: http://fusejs.io/

### Cool, but didn't use

- Bearhug: https://github.com/jharding/bearhug
