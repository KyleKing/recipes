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

import webbrowser
from pathlib import Path

from dash_dev import LOGGER_CONFIG
from dash_dev.doit_helpers.base import debug_task
from dash_dev.doit_helpers.doit_globals import DIG, DoItTask
from dash_dev.registered_tasks import *  # noqa: F401,F403,H303 skipcq: PYL-W0614 (Run 'doit list' to see tasks)
from doit.tools import LongRunning
from loguru import logger

logger.configure(**LOGGER_CONFIG)
logger.info('Starting DoIt tasks in dodo.py')

# Configure Dash paths
DIG.set_paths(source_path=Path(__file__).resolve().parent)

# Create list of all tasks run with `poetry run doit`. Comment on/off as needed
DOIT_CONFIG = {
    'action_string_formatting': 'old',  # Required for keyword-based tasks
    'default_tasks': [
        'main',
        # 'export_req', 'update_cl',
        # 'coverage',
        # # 'open_test_docs',
        'set_lint_config',
        'create_tag_file',
        # 'auto_format', # FIXME: this should ignore 'NO_TAG_SUM' and gitignore (i.e. /site/*)
        # 'document',
        # # 'open_docs',
        # 'lint_pre_commit',
        # 'type_checking',
    ],
}
"""DoIt Configuration Settings. Run with `poetry run doit`."""


def task_main() -> DoItTask:
    """Format markdown files.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([LongRunning('poetry run python main.py')])


def task_serve() -> DoItTask:
    """Serve the recipe site with `--dirtyreload` and open in a web browser.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([
        (webbrowser.open, ('http://localhost:8000', )),
        LongRunning('poetry run mkdocs serve --dirtyreload'),
    ])


def task_deploy() -> DoItTask:
    """Deploy to Github `gh-pages` branch.

    Returns:
        DoItTask: DoIt task

    """
    return debug_task([LongRunning('poetry run mkdocs gh-deploy')])
