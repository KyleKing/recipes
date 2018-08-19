# Recipes

Create interactive website for searching and making lists from user-specified source files

<details>
    <summary>Click to Open TOC</summary>
<!-- MarkdownTOC autolink="true" markdown_preview="github" -->

- [Development](#development)
- [Dev-Lower Priority](#dev-lower-priority)
- [Workflow](#workflow)
- [Libraries](#libraries)
    - [Cool, but didn't use](#cool-but-didnt-use)

<!-- /MarkdownTOC -->
</details>

## Development

- ~~Generate content with Crel~~
- ~~Highlight matches~~
- ~~Add search input bar and search on enter~~
- ~~Add all recipes by default~~
- ~~Sort alphabetically and with headers~~
- ~~Add table of contents using intermediary list with same index-mapping as localDB~~
- ~~Refactor for OOP~~
- ~~Revive (some) URL trickery~~
    + ~~Smooth scroll to recipe~~
    + ~~WONT FIX: smooth scroll to header ~~
    + Fix recipe linking on load
-  ~~Add Cody House navigation back ~~
- Add styles for input (only fixed at top if actively searching)
    + Add x button to clear the input
- Add scroll indicator at bottom

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
- Add flex-grid
    + Wrap TOC
    + Wrap Image, Ingredients, Recipe?
    + Guide: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Mastering_Wrapping_of_Flex_Items
- Mess with CSS
    + Try out different font face
    + Replace Skeleton?
        * Fix conflict of Skeleton with check boxes

- Add `make` mode with recipe in horizontal orientation
    + Can rotation of screen be locked with HTML?
        * https://stackoverflow.com/questions/43634583/prevent-landscape-orientation-mobile-website
        * https://www.google.com/search?rlz=1CDGOYI_enUS633US633&hl=en-US&ei=Jo1sW464M6Ht5gKBtKmwDA&q=ios+safari+prevent+web+mobile+rotation&oq=ios+safari+prevent+web+mobile+rotation
    + Track check box progress in URL (and cross out steps)
    + Add 'alt-ratio' toggle switch for common alternate ratio (maybe custom input with suggested ratio?)

## Dev-Lower Priority

- Add highlight for matches to 'group' (i.e. 'Brkfst') [Maybe insert highlighted text before recipe title?]

## Workflow

1. Create a `<recipe_title>.json` and matching `<recipe_title>.<img_format>` in the respective database directory. See `database\__template.json`.
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
