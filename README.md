# Recipes

Create interactive website for searching and making lists from user-specified source files

<details>
    <summary>Click to Open TOC</summary>
<!-- MarkdownTOC autolink="true" markdown_preview="github" -->

- [Quick Start](#quick-start)
- [Development - Archive](#development---archive)
- [Libraries](#libraries)
    - [Cool, but didn't use](#cool-but-didnt-use)

<!-- /MarkdownTOC -->
</details>

## Quick Start

1. Create a new `<recipe_title>.json` and matching `<recipe_title>.<img_format>` in the respective database subdirectory (i.e. breakfast/)
    - See `database\__template.json` as an example JSON file
2. Run `python make.py`, which will:
    - Move source images to `dist/imgs/<subdir>-<recipe_title>.<img_format>`
    - Combine JSON documents into single JSON file
        + Add recipe title from filename split on underscore
        + Add link to minified image
        + Standardize ingredients
        + Identify errors in source file
    - The JSON file is then converted to a JS file to get around XHR restrictions
3. With the updated database, open index.html in a browser

## Development - Archive

- Add flex-grid?
    + Wrap TOC
    + Wrap Image, Ingredients, Recipe?
    + Guide: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Mastering_Wrapping_of_Flex_Items
- Mess with CSS
    + Try out different font face
    + Replace Skeleton?
        * Fix conflict of Skeleton with check boxes
- Add `make` mode with a single recipe in horizontal orientation
    + Can rotation of screen be locked with HTML?
        * https://stackoverflow.com/questions/43634583/prevent-landscape-orientation-mobile-website
        * https://www.google.com/search?rlz=1CDGOYI_enUS633US633&hl=en-US&ei=Jo1sW464M6Ht5gKBtKmwDA&q=ios+safari+prevent+web+mobile+rotation&oq=ios+safari+prevent+web+mobile+rotation
    + Track make mode using URL
    + Keep state of ingredient check in URL
        * Possibly also cross out steps as completed?
    + Add 'alt-ratio' toggle to update ingredient amounts

## Libraries

- Crel for DOM creation: https://github.com/KoryNunn/crel
- Fuse for fuzzy-search: http://fusejs.io/
- Lazy Load: https://github.com/verlok/lazyload

### Cool, but didn't use

- Bearhug: https://github.com/jharding/bearhug
- CodyHouse: https://codyhouse.co/gem/3d-bold-navigation
