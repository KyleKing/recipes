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

import sys
from pathlib import Path

from calcipy.doit_tasks import *  # noqa: F401,F403,H303 (Run 'doit list' to see tasks). skipcq: PYL-W0614
from calcipy.doit_tasks import DOIT_CONFIG_RECOMMENDED
from calcipy.doit_tasks.doit_globals import DIG  # DEF_PATH_CODE_TAG_SUMMARY
from calcipy.log_helpers import build_logger_config
from loguru import logger

from recipes import __pkg_name__
from recipes.tasks import task_compress, task_convert_png_to_jpg, task_main  # noqa: F401I

# PLANNED: Move all of this into a function! (and/or task?)

logger.enable(__pkg_name__)  # This will enable output from calcipy, which is off by default
# See an example of toggling loguru at: https://github.com/KyleKing/calcipy/tree/examples/loguru-toggle

path_project = Path(__file__).resolve().parent
log_config = build_logger_config(path_project, production=False)
logger.configure(**log_config)
logger.info(
    'Started logging to {path_project}/.logs with {log_config}', path_project=path_project,
    log_config=log_config,
)

# FYI: Log the positional arguments
logger.debug('sys.argv={sys_argv}', sys_argv=sys.argv)

# Configure Dash paths
DIG.set_paths(path_project=path_project)

# FIXME: Needs to be fixed in calcipy
# PATH_CODE_TAG_SUMMARY = Path('docs/z_dev') / 'CODE_TAG_SUMMARY.md'  # DEF_PATH_CODE_TAG_SUMMARY.name
# DIG.ct.path_code_tag_summary = PATH_CODE_TAG_SUMMARY

DOIT_CONFIG = DOIT_CONFIG_RECOMMENDED
DOIT_CONFIG['default_tasks'].insert(0, 'main')  # Add the project-specific main task first
