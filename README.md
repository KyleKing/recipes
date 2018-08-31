# Recipes

Create interactive website for searching and making lists from user-specified source files

<details>
    <summary>Click to Open TOC</summary>
<!-- MarkdownTOC autolink="true" markdown_preview="github" -->

- [Development](#development)
- [Workflow](#workflow)
- [Libraries](#libraries)
    - [Cool, but didn't use](#cool-but-didnt-use)

<!-- /MarkdownTOC -->
</details>

## Development

- Add `make` mode with recipe in horizontal orientation
    + Fix recipe linking on load
    + Can rotation of screen be locked with HTML?
        * https://stackoverflow.com/questions/43634583/prevent-landscape-orientation-mobile-website
        * https://www.google.com/search?rlz=1CDGOYI_enUS633US633&hl=en-US&ei=Jo1sW464M6Ht5gKBtKmwDA&q=ios+safari+prevent+web+mobile+rotation&oq=ios+safari+prevent+web+mobile+rotation
    + Track check box progress in URL (and cross out steps)
    + Add 'alt-ratio' toggle switch for common alternate ratio (maybe custom input with suggested ratio?)
- Add flex-grid?
    + Wrap TOC
    + Wrap Image, Ingredients, Recipe?
    + Guide: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Mastering_Wrapping_of_Flex_Items
- Mess with CSS
    + Try out different font face
    + Replace Skeleton?
        * Fix conflict of Skeleton with check boxes
- Move to raw React to replace Crel
    - Look into React image lazy loaders: https://github.com/verlok/lazyload#usage-with-react

## Workflow

1. Create a `<recipe_title>.json` and matching `<recipe_title>.<img_format>` in the respective database subdirectory (i.e. breakfast/). See `database\__template.json`.
2. Run `python make.py`, which will:
    - Move source images to `dist/imgs/<subdir>-<recipe_title>.<img_format>`
    - Combine JSON documents into single JSON file
        + Add recipe title from filename split on underscore
        + Add link to minified image
        + Standardize ingredients
        + Identify errors in source file
3. Open index.html in a browser

## Libraries

- Crel for DOM creation: https://github.com/KoryNunn/crel
- Fuse for fuzzy-search: http://fusejs.io/
- Lazy Load: https://github.com/verlok/lazyload
- Inspiration from CodyHouse:

### Cool, but didn't use

- Bearhug: https://github.com/jharding/bearhug
