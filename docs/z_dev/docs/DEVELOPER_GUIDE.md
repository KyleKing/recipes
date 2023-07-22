# Developer Notes

## Local Development

```sh
git clone https://github.com/kyleking/recipes.git
cd recipes
poetry install --sync

# See the available tasks
poetry run calcipy
# Or use a local 'run' file (so that 'calcipy' can be extended)
./run

# Run the default task list (lint, auto-format, test coverage, etc.)
./run main

# Make code changes and run specific tasks as needed:
./run lint.fix test
```

## Publishing

For testing, create an account on [TestPyPi](https://test.pypi.org/legacy/). Replace `...` with the API token generated on TestPyPi or PyPi respectively

```sh
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi ...

./run main pack.publish --to-test-pypi
# If you didn't configure a token, you will need to provide your username and password to publish
```

To publish to the real PyPi

```sh
poetry config pypi-token.pypi ...
./run release

# Or for a pre-release
./run release --suffix=rc
```

## Current Status

<!-- {cts} COVERAGE -->
| File                   |   Statements |   Missing |   Excluded | Coverage   |
|------------------------|--------------|-----------|------------|------------|
| `recipes/__init__.py`  |           26 |         6 |          0 | 71.9%      |
| `recipes/formatter.py` |          105 |         1 |          0 | 98.7%      |
| `recipes/scripts.py`   |            7 |         7 |          0 | 0.0%       |
| `recipes/tasks.py`     |           39 |         7 |          0 | 80.7%      |
| **Totals**             |          177 |        21 |          0 | 87.4%      |

Generated on: 2023-07-22
<!-- {cte} -->
