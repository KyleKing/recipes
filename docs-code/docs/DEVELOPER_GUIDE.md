# Developer Notes

## Local Development

```sh
git clone https://github.com/kyleking/recipes.git
cd recipes
poetry install --sync
poetry run calcipy-pack pack.install-extras

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
| File                                              | Statements | Missing | Excluded | Coverage |
|---------------------------------------------------|-----------:|--------:|---------:|---------:|
| `recipes/__init__.py`                             | 4          | 0       | 0        | 100.0%   |
| `recipes/_calcipy_djot/__init__.py`               | 0          | 0       | 0        | 100.0%   |
| `recipes/_calcipy_djot/markup_table.py`           | 29         | 3       | 0        | 82.9%    |
| `recipes/_calcipy_djot/markup_writer/__init__.py` | 5          | 2       | 0        | 60.0%    |
| `recipes/_calcipy_djot/markup_writer/_writer.py`  | 93         | 30      | 0        | 66.7%    |
| `recipes/_runtime_type_check_setup.py`            | 13         | 0       | 37       | 100.0%   |
| `recipes/formatter.py`                            | 87         | 7       | 0        | 90.7%    |
| `recipes/scripts.py`                              | 5          | 5       | 0        | 0.0%     |
| `recipes/tasks.py`                                | 39         | 4       | 0        | 80.0%    |
| **Totals**                                        | 275        | 51      | 37       | 78.3%    |

Generated on: 2024-12-18
<!-- {cte} -->
