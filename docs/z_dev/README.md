# recipes

[mkdocs-material](https://squidfunk.github.io/mkdocs-material/)-based personal recipes website ([https://recipes.kyleking.me](https://recipes.kyleking.me))

## Installation

1. Clone the repository (`gh repo clon KyleKing/recipes`)
1. Run `poetry install`

## Usage

Locally, these are typical tasks for editing, previewing, and publishing the recipes

1. Create or edit markdown files in [`./docs/\*/\*.md`](https://github.com/KyleKing/recipes/tree/main/docs). For new recipes, use the [`./_recipe_template.md`](https://github.com/KyleKing/recipes/blob/main/_recipe_template.md)
1. Run `poetry run doit` to run all local tasks
1. Run `poetry run doit run format_recipes` to update the auto-formatted rating and image sections for the recipes
1. Run `poetry run doit run compress ./docs/path/` to reduce image file sizes. Can either be a directory or an individual file
1. Run `poetry run doit run open_docs` to preview the recipes website in a browser
1. Run `poetry run doit run main deploy_docs` to deploy to `gh-pages`

For more example code, see the [scripts] directory or the [tests].

## Project Status

See the `Open Issues` and/or the [CODE_TAG_SUMMARY]. For release history, see the [CHANGELOG].

## Contributing

We welcome pull requests! For your pull request to be accepted smoothly, we suggest that you first open a GitHub issue to discuss your idea. For resources on getting started with the code base, see the below documentation:

- [DEVELOPER_GUIDE]
- [STYLE_GUIDE]

## Code of Conduct

We follow the [Contributor Covenant Code of Conduct][contributor-covenant].

### Open Source Status

We try to reasonably meet most aspects of the "OpenSSF scorecard" from [Open Source Insights](https://deps.dev/pypi/recipes)

## Responsible Disclosure

If you have any security issue to report, please contact the project maintainers privately. You can reach us at [dev.act.kyle@gmail.com](mailto:dev.act.kyle@gmail.com).

## License

[LICENSE]

[changelog]: ./docs/CHANGELOG.md
[code_tag_summary]: ./docs/CODE_TAG_SUMMARY.md
[contributor-covenant]: https://www.contributor-covenant.org
[developer_guide]: ./docs/DEVELOPER_GUIDE.md
[license]: https://github.com/kyleking/recipes/LICENSE
[scripts]: https://github.com/kyleking/recipes/scripts
[style_guide]: ./docs/STYLE_GUIDE.md
[tests]: https://github.com/kyleking/recipes/tests
