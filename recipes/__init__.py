"""recipes."""

from contextlib import suppress
from enum import Enum
from os import getenv

from beartype import BeartypeConf
from beartype.claw import beartype_this_package
from beartype.typing import Self

__version__ = '0.4.0'
__pkg_name__ = 'recipes'


class _BeartypeModes(Enum):
    """Supported global beartype modes."""

    ERROR = 'ERROR'
    WARNING = 'WARNING'
    OFF = None

    @classmethod
    def from_environment(cls) -> Self:
        """Return the configured mode."""
        beartype_mode = getenv('BEARTYPE_MODE') or None
        try:
            return cls(beartype_mode)
        except ValueError:
            msg = f"'BEARTYPE_MODE={beartype_mode}' is not an allowed mode from {[_e.value for _e in cls]}"
            raise ValueError(
                msg,
            ) from None


def configure_beartype() -> None:
    """Optionally configure beartype globally."""
    beartype_mode = _BeartypeModes.from_environment()
    is_stdout = True

    if beartype_mode != _BeartypeModes.OFF:
        conf = {}
        if beartype_mode == _BeartypeModes.ERROR:
            conf['warning_cls_on_decorator_exception'] = None

        with suppress(ImportError):
            from beartype._util.os.utilostty import is_stdout_terminal
            is_stdout = is_stdout_terminal()
        if getenv('BEARTYPE_NO_COLOR') or not is_stdout:
            conf['is_color'] = False

        beartype_this_package(conf=BeartypeConf(**conf))


configure_beartype()

# ====== Above is the recommended code from calcipy_template and may be updated on new releases ======
