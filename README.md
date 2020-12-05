# Recipes

[mkdocs-material](https://squidfunk.github.io/mkdocs-material/)-based recipe website ([https://kyleking.me/recipes](https://kyleking.me/recipes))

## Quick Start

## Configuration

1. Clone the repository (`git clone https://github.com/KyleKing/recipes.git`)
2. Run `poetry install`

## Development

Typical tasks for editing, previewing, and publishing the recipes

1. Create or edit markdown files in [./docs/\*/\*.md](./docs/). For new recipes, use the [./_recipe_template.md](./_recipe_template.md)
2. Run `poetry run doit run main` to update auto-formatted sections and optimize images
3. Run `poetry run doit run serve` to preview the changes in a browser
4. Run `poetry run doit` to push the publish the new version (could call `poetry run doit run deploy` directly, but this skips tasks that check local code)
