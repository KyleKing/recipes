# Developer Notes

## Local Development

```sh
git clone https://github.com/kyleking/recipes.git
cd recipes
poetry install

# See the available tasks
poetry run doit list

# Run the default task list (lint, auto-format, test coverage, etc.)
poetry run doit --continue

# Make code changes and run specific tasks as needed:
poetry run doit run test
```

## Publishing

For testing, create an account on [TestPyPi](https://test.pypi.org/legacy/). Replace `...` with the API token generated on TestPyPi|PyPi respectively

```sh
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi ...

poetry run doit run publish_test_pypi
# If you didn't configure a token, you will need to provide your username and password to publish
```

To publish to the real PyPi

```sh
poetry config pypi-token.pypi ...
poetry run doit run publish

# For a full release, increment the version, the documentation, and publish
poetry run doit run --continue
poetry run doit run cl_bump document deploy_docs publish
# Note: cl_bump_pre is helpful for pre-releases rather than full increments
```

## Current Status

<!-- {cts} COVERAGE -->
| File                   |   Statements |   Missing |   Excluded | Coverage   |
|:-----------------------|-------------:|----------:|-----------:|:-----------|
| `recipes/__init__.py`  |            4 |         0 |          0 | 100.0%     |
| `recipes/formatter.py` |          104 |       104 |          0 | 0.0%       |
| `recipes/tasks.py`     |           38 |        38 |          0 | 0.0%       |
| **Totals**             |          146 |       142 |          0 | 2.7%       |

Generated on: 2022-02-01T21:39:48.330417
<!-- {cte} -->
