"""Compatibility launcher: python main.py (works from any working directory)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from space_invaders.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
