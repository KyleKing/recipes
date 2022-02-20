"""recipes."""

from loguru import logger

__version__ = '0.3.0'
__pkg_name__ = 'recipes'

logger.disable(__pkg_name__)

# ====== Above is the recommended code from calcipy_template and may be updated on new releases ======

__all__ = ['__version__', '__pkg_name__']
