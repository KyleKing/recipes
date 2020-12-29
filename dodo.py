"""doit Script.

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

from calcipy.doit_tasks import *  # noqa: F401,F403,H303 (Run 'doit list' to see tasks). skipcq: PYL-W0614
from calcipy.doit_tasks import DOIT_CONFIG_RECOMMENDED
from calcipy.doit_tasks.doit_globals import DIG
from calcipy.log_helpers import build_logger_config
from loguru import logger

from recipes import __pkg_name__
from recipes.tasks import task_compress, task_deploy, task_main, task_serve  # noqa: F401I

logger.enable(__pkg_name__)
path_parent = Path(__file__).resolve().parent
log_config = build_logger_config(path_parent, production=False)
logger.configure(**log_config)
logger.info(
    'Started logging to {path_parent}/.logs with {log_config}', path_parent=path_parent,
    log_config=log_config,
)

# Configure Dash paths
DIG.set_paths(path_project=path_parent)

# Create list of all tasks run with `poetry run doit`. Comment on/off as needed
DOIT_CONFIG = {
    'action_string_formatting': 'old',  # Required for keyword-based tasks
    'default_tasks': [
        'main',
        'coverage',
        # 'open_test_docs',
        'create_tag_file',
        'auto_format',
        # 'deploy',
    ],
}
"""DoIt Configuration Settings. Run with `poetry run doit`."""
