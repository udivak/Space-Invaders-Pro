import os

# Must be set before pygame creates a display or mixer anywhere in the test run.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import random
import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from space_invaders.assets import IMAGE_FILES  # noqa: E402

# Real sprite sizes; synthetic surfaces are fully opaque rectangles of the same size.
SIZES = {
    "enemy_red": (70, 50), "enemy_green": (70, 50), "enemy_blue": (70, 50),
    "player": (88, 90), "player2": (88, 90), "boss_grey": (110, 204),
    "player_laser": (58, 100), "player2_laser": (58, 100), "boss_laser": (70, 93),
    "enemy_laser_blue": (66, 88), "enemy_laser_red": (64, 88), "enemy_laser_green": (66, 88),
    "background": (950, 750), "pack_hp": (70, 39), "pack_triple_laser": (83, 50), "pack_shield": (73, 60),
}
assert set(SIZES) == set(IMAGE_FILES)


def make_images():
    images = {}
    for key, size in SIZES.items():
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((255, 255, 255, 255))
        images[key] = surface
    return images


@pytest.fixture
def images():
    return make_images()


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Every test writes user data only below its own temporary directory."""
    data = tmp_path / "user-data"
    monkeypatch.setenv("SPACE_INVADERS_DATA_DIR", str(data))
    monkeypatch.delenv("SPACE_INVADERS_LEGACY_ENCODING", raising=False)
    return data


class ScriptedRandom(random.Random):
    """Seeded RNG whose enemy-fire draws never fire unless forced."""

    def __init__(self, seed=0, fire=False):
        super().__init__(seed)
        self.fire = fire

    def randrange(self, start, stop=None, step=1):
        if (start, stop) == (0, 70):
            return 1 if self.fire else 0
        return super().randrange(start, stop, step)


@pytest.fixture(scope="session", autouse=True)
def repository_scores_unchanged():
    """The historical scores.txt must be byte-identical after the whole run, whatever it contains."""
    path = ROOT / "scores.txt"
    before = path.read_bytes() if path.exists() else None
    yield
    assert (path.read_bytes() if path.exists() else None) == before


class Keys(dict):
    """Keyboard state with nothing held."""
    def __missing__(self, k):
        return False


@pytest.fixture
def ctx(images, tmp_path):
    """Screen context with synthetic images, fonts and temporary score/preference files."""
    from space_invaders.app import Context, make_fonts
    from space_invaders.assets import AssetBundle
    from space_invaders.preferences import Preferences
    from space_invaders.scores import ScoreStore
    pygame.font.init()
    return Context(AssetBundle(images), make_fonts(), ScoreStore(tmp_path / "data"), Preferences(),
                   tmp_path / "data" / "settings.json", key_state=Keys, rng_factory=lambda: random.Random(1))


@pytest.fixture
def surface():
    return pygame.Surface((950, 750))
