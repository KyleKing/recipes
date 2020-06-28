# Recipes

Create interactive website for searching and making lists from user-specified source files

<details>
    <summary>Click to Open TOC</summary>
<!-- MarkdownTOC autolink="true" markdown_preview="github" -->

- [Quick Start](#quick-start)
- [Libraries](#libraries)
    - [Cool, but didn't use](#cool-but-didnt-use)

<!-- /MarkdownTOC -->
</details>

## Quick Start

1. Create a new `<recipe_title>.json` and matching `<recipe_title>.<img_format>` in the respective database subdirectory (i.e. breakfast/)
    - See `database\__template.json` as an example JSON file
2. Run `poetry run python make.py`, which will:
    - Move source images to `dist/imgs/<subdir>-<recipe_title>.<img_format>`
    - Combine JSON documents into single JSON file
        + Add recipe title from filename split on underscore
        + Add link to minified image
        + Standardize ingredients
        + Identify errors in source file
    - The JSON file is then converted to a JS file to get around XHR restrictions
3. With the updated database, open index.html in a browser

## Libraries

- Crel for DOM creation: https://github.com/KoryNunn/crel
- Fuse for fuzzy-search: http://fusejs.io/
- Lazy Load: https://github.com/verlok/lazyload

### Cool, but didn't use

- Bearhug: https://github.com/jharding/bearhug
- CodyHouse: https://codyhouse.co/gem/3d-bold-navigation
