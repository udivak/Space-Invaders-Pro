"""Integration: real media under dummy SDL drivers, complete lifecycle and fresh-process startup."""
import gc
import os
import random
import subprocess
import sys
import textwrap
import weakref
from pathlib import Path

import pygame
import pytest

from space_invaders import app as app_module
from space_invaders.assets import AssetError, load_assets
from space_invaders.preferences import Preferences
from space_invaders.scores import ScoreStore, read_scores
from space_invaders.screens import GameOverScreen, GameplayScreen, MenuScreen, ScoresScreen

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parent.parent


def key(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


class Keys(dict):
    def __missing__(self, k):
        return False


@pytest.fixture
def real_ctx(tmp_path):
    pygame.display.init()
    pygame.font.init()
    surface = pygame.display.set_mode((950, 750))
    bundle = load_assets(audio_enabled=False)
    ctx = app_module.Context(bundle, app_module.make_fonts(), ScoreStore(tmp_path / "data"), Preferences(),
                             tmp_path / "data" / "settings.json", key_state=Keys,
                             rng_factory=lambda: random.Random(4))
    yield ctx, surface
    pygame.display.quit()


def test_real_assets_load_and_every_image_is_used(real_ctx):
    ctx, _ = real_ctx
    assert set(ctx.assets.images) >= {"player", "boss_grey", "pack_hp", "background"}
    assert ctx.assets.images["background"].get_size() == (950, 750)
    assert not ctx.assets.audio_enabled


@pytest.mark.parametrize("mode_index,mode", [(0, "solo"), (1, "coop")])
def test_complete_lifecycle_repeated(real_ctx, mode_index, mode):
    ctx, surface = real_ctx
    app = app_module.App(ctx)
    sessions = []
    for cycle in range(20):
        assert isinstance(app.screen, MenuScreen)
        app.step([pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.screen.buttons.rect(mode_index).center,
                                     button=1)], 1 / 60)
        app.draw(surface)
        app.step([key(pygame.K_RETURN)], 1 / 60)
        gameplay = app.screen
        assert isinstance(gameplay, GameplayScreen) and gameplay.mode == mode
        sessions.append(weakref.ref(gameplay.session))
        for _ in range(5):
            app.step([], 1 / 60)
            app.draw(surface)
        gameplay.session.invasions = 0
        for _ in range(120):
            app.step([], 1 / 60)
            app.draw(surface)
            if isinstance(app.screen, GameOverScreen):
                break
        assert isinstance(app.screen, GameOverScreen)
        app.step([key(0, c) for c in f"run{cycle}"] + [key(pygame.K_RETURN)], 1 / 60)
        assert isinstance(app.screen, ScoresScreen)
        app.draw(surface)
        app.step([key(pygame.K_ESCAPE)], 1 / 60)
        del gameplay
    records = read_scores(ctx.store.path)[0]
    assert len(records) == 20 and {r.mode for r in records} == {mode}
    gc.collect()
    assert sum(ref() is not None for ref in sessions) == 0      # replaced sessions are released


def test_missing_required_image_is_reported(tmp_path):
    (tmp_path / "assets").mkdir()
    pygame.display.init()
    try:
        with pytest.raises(AssetError, match="Required image is missing"):
            load_assets(tmp_path, audio_enabled=False)
    finally:
        pygame.display.quit()


# -- fresh processes ----------------------------------------------------------------
def run_python(code, tmp_path, cwd=None, extra_env=None):
    """code: a snippet or a list of snippets, each dedented separately."""
    code = "\n".join(textwrap.dedent(part) for part in ([code] if isinstance(code, str) else code))
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1",
               SPACE_INVADERS_DATA_DIR=str(tmp_path / "data"), PYTHONPATH=str(ROOT))
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "-c", code], cwd=cwd or tmp_path, env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("order", [("space_invaders.app", "main"), ("main", "space_invaders.app"),
                                   ("space_invaders.entities", "space_invaders.screens"),
                                   ("space_invaders.__main__",)])
def test_imports_are_inert_in_any_order(tmp_path, order):
    out = run_python(f"""
        import importlib, pygame
        for name in {order!r}:
            importlib.import_module(name)
        assert not pygame.display.get_init() and not pygame.mixer.get_init() and not pygame.font.get_init()
        print("ok")
    """, tmp_path)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
    assert not (tmp_path / "data").exists()


QUIT_AFTER_FRAMES = """
    import pygame
    real_get = pygame.event.get
    frames = [0]
    def fake_get(*args, **kwargs):
        frames[0] += 1
        real_get()
        return [pygame.event.Event(pygame.QUIT)] if frames[0] > 3 else []
    pygame.event.get = fake_get
"""


@pytest.mark.parametrize("launcher", ["main_path", "module"])
def test_launchers_start_and_quit_from_another_directory(tmp_path, launcher):
    elsewhere = tmp_path / "some other dir"
    elsewhere.mkdir()
    if launcher == "main_path":
        start = f"import runpy, sys; sys.argv = ['main.py']; runpy.run_path({str(ROOT / 'main.py')!r}, run_name='__main__')"
    else:
        start = "import runpy, sys; runpy.run_module('space_invaders', run_name='__main__')"
    out = run_python([QUIT_AFTER_FRAMES, start], tmp_path, cwd=elsewhere)
    assert out.returncode == 0, out.stderr
    assert list(elsewhere.iterdir()) == []                     # nothing written to the working directory
    assert (tmp_path / "data" / "scores.csv").is_file()         # legacy history migrated into the data root


def test_startup_without_audio_device(tmp_path):
    out = run_python([QUIT_AFTER_FRAMES, """
    import pygame, sys
    def no_mixer(*a, **k):
        raise pygame.error("no audio device")
    pygame.mixer.init = no_mixer
    from space_invaders.app import run
    sys.exit(run())
    """], tmp_path)
    assert out.returncode == 0, out.stderr
    assert "audio disabled" in out.stderr


def test_invalid_data_dir_is_actionable(tmp_path):
    out = run_python("import sys\nfrom space_invaders.app import run\nsys.exit(run())", tmp_path,
                     extra_env={"SPACE_INVADERS_DATA_DIR": "relative/path"})
    assert out.returncode == 2 and "must be a nonempty absolute directory path" in out.stderr


def test_startup_reports_skipped_legacy_lines(tmp_path, monkeypatch):
    legacy = tmp_path / "scores.txt"
    legacy.write_bytes(b"(old, 9)\nbroken\n")
    monkeypatch.setattr(app_module.paths, "legacy_scores_path", lambda: legacy)
    try:
        _, ctx, notice = app_module._startup({"SPACE_INVADERS_DATA_DIR": str(tmp_path / "data")})
        assert "1 unreadable line(s) skipped" in notice
        assert [r.name for r in read_scores(ctx.store.path)[0]] == ["old"]
    finally:
        pygame.quit()
