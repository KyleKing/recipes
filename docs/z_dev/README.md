# recipes

[mkdocs-material](https://squidfunk.github.io/mkdocs-material/)-based recipe website ([https://recipes.kyleking.me](https://recipes.kyleking.me))

## Installation

1. Clone the repository (`git clone https://github.com/KyleKing/recipes.git`)
2. Run `poetry install`

## Usage

Locally, these are typical tasks for editing, previewing, and publishing the recipes

<!-- TODO: Update with changes from calcipy! -->

1. Create or edit markdown files in [./docs/\*/\*.md](https://github.com/KyleKing/recipes/tree/main/docs). For new recipes, use the [./_recipe_template.md](https://github.com/KyleKing/recipes/blob/main/_recipe_template.md)
2. Run `poetry run doit` to run all local tasks
3. Run `poetry run doit run main` to update auto-formatted sections
4. Run `poetry run doit run compress ./docs/path/` to reduce image file sizes. Can either be a directory or an individual file
5. Run `poetry run doit run serve_fast` to preview the website in a browser
6. Run `poetry run doit run main deploy` to deploy to gh-pages

## Roadmap

See the `Open Issues` and `Milestones` for current status and [./docs/CODE_TAG_SUMMARY.md](./docs/CODE_TAG_SUMMARY.md) for annotations in the source code.

For release history, see the [./docs/CHANGELOG.md](./docs/CHANGELOG.md)

## Contributing

See the Developer Guide, Contribution Guidelines, etc

- [./docs/DEVELOPER_GUIDE.md](./docs/DEVELOPER_GUIDE.md)
- [./docs/STYLE_GUIDE.md](./docs/STYLE_GUIDE.md)
- [./docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md)
- [./docs/CODE_OF_CONDUCT.md](./docs/CODE_OF_CONDUCT.md)
- [./docs/SECURITY.md](./docs/SECURITY.md)

## License

[LICENSE](https://github.com/kyleking/recipes/LICENSE)
