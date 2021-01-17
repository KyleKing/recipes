# Recipes

[mkdocs-material](https://squidfunk.github.io/mkdocs-material/)-based recipe website ([https://recipes.kyleking.me](https://recipes.kyleking.me))

## Quick Start

## Configuration

1. Clone the repository (`git clone https://github.com/KyleKing/recipes.git`)
2. Run `poetry install`

## Development

Typical tasks for editing, previewing, and publishing the recipes

1. Create or edit markdown files in [./docs/\*/\*.md](./docs/). For new recipes, use the [./_recipe_template.md](./_recipe_template.md)
2. Run `poetry run doit` to run local tests and checks
3. Run `poetry run doit run main` to update auto-formatted sections
4. Run `poetry run doit run compress ./docs/path/` to reduce image file sizes. Can either be a directory or an individual file
5. Run `poetry run doit run serve` to preview the website in a browser
6. Run `poetry run doit run main deploy` to deploy to gh-pages
