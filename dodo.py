"""DoIt Script.

```sh
# Ensure that packages are installed
poetry install
# List Tasks
poetry run doit list
# (Or use a poetry shell)
# > poetry shell
# > doit list

# Run tasks individually (examples below)
poetry doit run coverage open_test_docs
poetry doit run set_lint_config create_tag_file document
# Or all of the tasks in DOIT_CONFIG
poetry run doit
```

"""

from pathlib import Path

from dash_dev import LOGGER_CONFIG
from dash_dev.doit_helpers.doit_globals import DIG
from dash_dev.registered_tasks import *  # noqa: F401,F403,H303 skipcq: PYL-W0614 (Run 'doit list' to see tasks)
from loguru import logger

logger.configure(**LOGGER_CONFIG)
logger.info('Starting DoIt tasks in dodo.py')

# Configure Dash paths
DIG.set_paths(source_path=Path(__file__).resolve().parent)

# Create list of all tasks run with `poetry run doit`. Comment on/off as needed
DOIT_CONFIG = {
    'action_string_formatting': 'old',  # Required for keyword-based tasks
    'default_tasks': [
        # 'export_req', 'update_cl',
        # 'coverage',
        # # 'open_test_docs',
        'set_lint_config',
        # 'create_tag_file',
        # 'auto_format',
        # 'document',
        # # 'open_docs',
        # 'lint_pre_commit',
        # # 'type_checking',
    ],
}
"""DoIt Configuration Settings. Run with `poetry run doit`."""