"""maps-sll: homogeneous local systems (SLO) around centralities."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("maps-sll")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"
