# Recipes

Create interactive website for searching and making lists from user-specified source files

## Development

- -Generate content with Crel-
- -Highlight matches-
- Add search input bar (and search on 'enter'?)
- Add initial display with title sections
- Add Cody House navigation back
- Try out different font face
- Replace Skeleton with standard flex-grid: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Mastering_Wrapping_of_Flex_Items
    + Have image/ingredients/recipes/notes wrap
- Can other modernizer scripts be dropped?
- Add 'make' mode with recipe in horizontal orientation
    + Can rotation of screen be locked with HTML?
        * https://stackoverflow.com/questions/43634583/prevent-landscape-orientation-mobile-website
        * https://www.google.com/search?rlz=1CDGOYI_enUS633US633&hl=en-US&ei=Jo1sW464M6Ht5gKBtKmwDA&q=ios+safari+prevent+web+mobile+rotation&oq=ios+safari+prevent+web+mobile+rotation

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
