"""Regressions for the second code inspection (IR-01..IR-05)."""
import random

import pygame
import pytest

from space_invaders import preferences
from space_invaders.app import App
from space_invaders.gameplay import Feedback
from space_invaders.scores import ScoreRecord, ScoreStore, parse_legacy
from space_invaders.screens import GameplayScreen, InstructionsScreen, MenuScreen, PauseScreen, ScoresScreen
from test_screens import key


def focus_lost():
    return pygame.event.Event(pygame.WINDOWFOCUSLOST)


def test_control_characters_in_names_render(ctx, surface):
    ctx.store.save(ScoreRecord("r1", "A\x00B\x07", 5, "solo", 1, "modern-v1"))
    legacy = ctx.store.path.parent.parent / "legacy.txt"
    legacy.write_bytes(b"(N\x00UL, 3)\n")
    screen = ScoresScreen(ctx, ("solo", "modern-v1"), "notice with \x00 inside")
    screen.draw(surface)
    records, _ = parse_legacy(legacy.read_text())
    assert records[0].name == "N\x00UL"                     # stored data is preserved
    MenuScreen(ctx, "bad \x00 notice").draw(surface)


def test_focus_lost_with_transition_into_gameplay_pauses(ctx):
    app = App(ctx)
    app.screen = InstructionsScreen(ctx, "solo")
    app.step([key(pygame.K_RETURN), focus_lost()], 1 / 60)
    assert isinstance(app.screen, PauseScreen)
    app.step([key(pygame.K_ESCAPE)], 1 / 60)                  # explicit resume while still unfocused
    assert isinstance(app.screen, PauseScreen)
    assert app.screen.gameplay.session.ticks == 0
    app.step([pygame.event.Event(pygame.WINDOWFOCUSGAINED)], 1 / 60)
    assert isinstance(app.screen, PauseScreen)                # regaining focus never auto-resumes
    app.step([key(pygame.K_ESCAPE)], 1 / 60)
    assert isinstance(app.screen, GameplayScreen)


def test_focus_lost_with_resume_stays_paused(ctx):
    app = App(ctx)
    app.screen = gameplay = GameplayScreen(ctx, "solo", random.Random(1))
    app.step([key(pygame.K_ESCAPE)], 1 / 60)
    app.step([key(pygame.K_ESCAPE), focus_lost()], 1 / 60)
    assert isinstance(app.screen, PauseScreen) and app.screen.gameplay is gameplay
    app.step([key(pygame.K_r), focus_lost()], 1 / 60)          # restart while unfocused
    assert isinstance(app.screen, PauseScreen) and app.screen.gameplay is not gameplay


@pytest.mark.parametrize("content", ['{"music_volume": 1' + "0" * 400 + '}',
                                     '{"music_volume": ' + "9" * 5000 + '}',
                                     '{"music_volume": NaN, "effects_volume": -Infinity}',
                                     '{"reduced_effects": 1}'])
def test_invalid_preference_numbers_do_not_crash(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    prefs, notice = preferences.load(path)
    assert 0.0 <= prefs.music_volume <= 1.0 and 0.0 <= prefs.effects_volume <= 1.0
    assert isinstance(prefs.reduced_effects, bool)


def test_oversized_preference_clamps_with_no_crash(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"music_volume": 1' + "0" * 400 + '}', encoding="utf-8")
    assert preferences.load(path)[0].music_volume == 1.0


def test_huge_legacy_score_is_a_line_warning(tmp_path):
    records, warnings = parse_legacy("(ok, 3)\n(big, " + "9" * 5000 + ")\n")
    assert [r.name for r in records] == ["ok"] and warnings[0].startswith("legacy line 2")
    legacy = tmp_path / "scores.txt"
    legacy.write_text("(ok, 3)\n(big, " + "9" * 5000 + ")\n")
    store = ScoreStore(tmp_path / "data", legacy)
    assert len(store.load()[0]) == 1
    assert store.save(ScoreRecord("r1", "n", 1, "solo", 1, "modern-v1"))
    assert "1 unreadable line(s) skipped" in store.migration_notice()


def test_hit_flash_survives_a_long_catch_up_frame(ctx):
    screen = GameplayScreen(ctx, "solo", random.Random(1))
    target = screen.session.players[0]
    real_step = screen.session.update_step

    def step_with_hit(actions=()):
        real_step(actions)
        screen.session.feedback.append(Feedback("player_hit", target.x, target.y, target))
    screen.session.update_step = step_with_hit
    screen.update(0.1)                                          # six ticks in one frame
    assert id(target) in screen.effects.flashes                 # visible on the first draw
