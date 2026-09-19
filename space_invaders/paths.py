"""Read-only resource root and writable per-user data root. No I/O at import."""
import os
import sys
from pathlib import Path

DATA_DIR_ENV = "SPACE_INVADERS_DATA_DIR"


def resource_root():
    """Directory containing assets/ and sounds/ (repository root or bundle root)."""
    return Path(__file__).resolve().parent.parent


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def data_dir(environ=None, platform=None, home=None):
    """Writable data directory; does not create it."""
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    override = environ.get(DATA_DIR_ENV)
    if override is not None:
        if not override.strip() or not os.path.isabs(override):
            raise ValueError(f"{DATA_DIR_ENV} must be a nonempty absolute directory path, got {override!r}")
        path = Path(override)
        if path.exists() and not path.is_dir():
            raise ValueError(f"{DATA_DIR_ENV} points to a file, not a directory: {override}")
        return path
    if platform.startswith("win"):
        base = environ.get("LOCALAPPDATA")
        return Path(base) / "SpaceInvaders" if base else home / "AppData" / "Local" / "SpaceInvaders"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "SpaceInvaders"
    base = environ.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / "space-invaders"


def legacy_scores_path():
    """The repository's historical scores.txt; only used in source (non-frozen) mode."""
    return resource_root() / "scores.txt"
