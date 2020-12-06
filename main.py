"""Format the markdown files."""

import sys

from loguru import logger

from recipes import __pkg_name__, formatter

if __name__ == '__main__':
    logger.enable(__pkg_name__)
    logger.remove()
    logger.add(sys.stdout, level='INFO')
    formatter.run()
