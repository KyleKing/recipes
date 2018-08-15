# Recipes

Create interactive website for searching and making lists from user-specified source files

## Development

- ~~Generate content with Crel~~
- ~~Highlight matches~~
- ~~Add search input bar and search on enter~~
- ~~Add all recipes by default~~
- ~~Sort alphabetically and with headers~~
- Add table of contents
- Revive URL trickery
    + Implement linking on load, by only loading a specific recipe
        * Combine all TOC as one list, get index, use index from local database
- Add Cody House navigation back
- Add styles for input (fix at top)
    + Test on mobile / localtunnel
- Lazy load images (which library?)
    + Guides
        * Medium: https://medium.freecodecamp.org/using-svg-as-placeholders-more-image-loading-techniques-bed1b810ab2c
        * Trivago Engineer: https://matthias-endler.de/2017/image-previews/
        * Demo of simple, artistic outlines: https://codepen.io/ainalem/details/aLKxjm
    + Libraries
        * *SQIP* (SVG-based LQIP): https://github.com/technopagan/sqip
        * geometrize: https://www.geometrize.co.uk/
        * primitive.nextgen: https://github.com/cielito-lindo-productions/primitive.nextgen
        * justlazy: http://fhopeman.github.io/justlazy/#demo
        * beLazy: http://dinbror.dk/blazy/
- Try out different font face
- Replace Skeleton with standard flex-grid: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Mastering_Wrapping_of_Flex_Items
    + Have image/ingredients/recipes/notes wrap

- Add 'make' mode with recipe in horizontal orientation
    + Can rotation of screen be locked with HTML?
        * https://stackoverflow.com/questions/43634583/prevent-landscape-orientation-mobile-website
        * https://www.google.com/search?rlz=1CDGOYI_enUS633US633&hl=en-US&ei=Jo1sW464M6Ht5gKBtKmwDA&q=ios+safari+prevent+web+mobile+rotation&oq=ios+safari+prevent+web+mobile+rotation

## Dev-Lower Priority

- Add highlight for matches to 'group' (i.e. 'Brkfst') [Maybe insert highlighted text before recipe title?]

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
