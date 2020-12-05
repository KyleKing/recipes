"""Format the markdown files."""

import sys

from loguru import logger

from recipes import formatter

if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stdout, level='INFO')
    formatter.run()
