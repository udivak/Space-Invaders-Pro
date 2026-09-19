"""Frame-level screens and App transitions with synthetic assets and constructed events."""
import random

import pygame
import pytest

from space_invaders.app import App
from space_invaders.gameplay import RunResult
from space_invaders.preferences import Preferences
from space_invaders.scores import ScoreRecord, ScoreStore, read_scores
from space_invaders.screens import (GameOverScreen, GameplayScreen, InstructionsScreen, MenuScreen,
                                    PauseScreen, ScoresScreen, SettingsScreen)


def key(k, unicode="", mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=mod)


def click(pos, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def result(mode="solo", run_id="run-1"):
    kills = (3,) if mode == "solo" else (3, 4)
    return RunResult(run_id, mode, "modern-v1", 4, kills, 10, "breaches")


def test_menu_keyboard_focus_wraps_and_activates(ctx):
    menu = MenuScreen(ctx)
    assert menu.handle_events([key(pygame.K_UP)]) is None and menu.buttons.focus == 4
    assert menu.handle_events([key(pygame.K_TAB)]) is None and menu.buttons.focus == 0
    assert menu.handle_events([key(pygame.K_TAB, mod=pygame.KMOD_SHIFT)]) is None and menu.buttons.focus == 4
    menu.handle_events([key(pygame.K_DOWN), key(pygame.K_DOWN)])
    t = menu.handle_events([key(pygame.K_RETURN)])
    assert (t.target, t.mode) == ("instructions", "coop")


def test_menu_click_uses_event_position(ctx):
    menu = MenuScreen(ctx)
    rect = menu.buttons.rect(0)
    t = menu.handle_events([click(rect.center)])
    assert (t.target, t.mode) == ("instructions", "solo")
    assert menu.handle_events([click((5, 5))]) is None


def test_mode_is_explicit_on_each_selection(ctx):                                    # B7: 2 -> 1 -> 2
    app = App(ctx)
    modes = []
    for index in (1, 0, 1):
        app.screen = MenuScreen(ctx)
        app.step([click(app.screen.buttons.rect(index).center)], 0)
        assert isinstance(app.screen, InstructionsScreen)
        lines = [text for text, _ in app.screen.lines()]
        app.step([key(pygame.K_RETURN)], 0)
        modes.append((app.screen.mode, len(app.screen.session.players), any("Player 2" in l for l in lines)))
    assert modes == [("coop", 2, True), ("solo", 1, False), ("coop", 2, True)]


def test_transition_discards_rest_of_batch(ctx):
    app = App(ctx)
    rect = app.screen.buttons.rect(0)
    app.step([click(rect.center), click(rect.center), key(pygame.K_RETURN)], 0)
    assert isinstance(app.screen, InstructionsScreen)       # the second click did not start the game


def test_quit_wins_over_other_input(ctx):
    app = App(ctx)
    assert app.step([click(app.screen.buttons.rect(0).center), pygame.event.Event(pygame.QUIT)], 0) is False
    assert isinstance(app.screen, MenuScreen)


def test_instructions_escape_returns_to_menu(ctx):
    assert InstructionsScreen(ctx, "solo").handle_events([key(pygame.K_ESCAPE)]).target == "menu"
    assert InstructionsScreen(ctx, "solo").handle_events([key(pygame.K_SPACE)]).target == "gameplay"


def test_pause_freezes_and_resume_returns_same_session(ctx):
    app = App(ctx)
    app.screen = gameplay = GameplayScreen(ctx, "solo", random.Random(2))
    for _ in range(30):
        app.step([], 1 / 60)
    app.step([key(pygame.K_ESCAPE)], 1 / 60)
    assert isinstance(app.screen, PauseScreen)
    ticks = gameplay.session.ticks
    for _ in range(600):                                    # ten paused seconds
        app.step([], 1 / 60)
    assert gameplay.session.ticks == ticks
    app.step([key(pygame.K_ESCAPE)], 1 / 60)
    assert app.screen is gameplay and gameplay.accumulator == 0.0
    app.step([], 1 / 60)
    assert gameplay.session.ticks == ticks + 1


def test_focus_loss_pauses_and_does_not_auto_resume(ctx):
    app = App(ctx)
    app.screen = GameplayScreen(ctx, "solo", random.Random(2))
    app.step([pygame.event.Event(pygame.WINDOWFOCUSLOST)], 1 / 60)
    assert isinstance(app.screen, PauseScreen)
    app.step([pygame.event.Event(pygame.WINDOWFOCUSGAINED)], 1 / 60)
    assert isinstance(app.screen, PauseScreen)


def test_pause_restart_creates_fresh_session_and_menu_abandons(ctx):
    app = App(ctx)
    app.screen = old = GameplayScreen(ctx, "coop", random.Random(2))
    for _ in range(10):
        app.step([], 1 / 60)
    app.step([key(pygame.K_ESCAPE)], 0)
    app.step([key(pygame.K_r)], 0)
    assert isinstance(app.screen, GameplayScreen) and app.screen is not old
    assert app.screen.mode == "coop" and app.screen.session.ticks == 0
    assert app.screen.session.run_id != old.session.run_id
    app.step([key(pygame.K_ESCAPE)], 0)
    pause = app.screen
    app.step([click(pause.buttons.rect(2).center)], 0)
    assert isinstance(app.screen, MenuScreen)
    assert not ctx.store.path.exists()                      # abandoned run is never saved


def test_defeat_shows_ending_then_results(ctx):
    app = App(ctx)
    app.screen = gameplay = GameplayScreen(ctx, "solo", random.Random(2))
    app.step([], 1 / 60)
    gameplay.session.invasions = 0
    app.step([], 1 / 60)
    assert gameplay.session.defeated
    for _ in range(80):                                      # < 1.5 s: still showing the ending
        assert app.step([key(pygame.K_ESCAPE)], 1 / 60)
    assert app.screen is gameplay
    for _ in range(20):
        app.step([], 1 / 60)
    assert isinstance(app.screen, GameOverScreen)
    assert app.screen.result.defeat_reason == "breaches"


def type_name(screen, text):
    return screen.handle_events([key(0, ch) for ch in text] + [key(pygame.K_RETURN)])


def test_name_entry_saves_once_and_opens_bucket(ctx):
    screen = GameOverScreen(ctx, result("coop"))
    t = type_name(screen, "  Team  ")
    assert (t.target, t.bucket) == ("scores", ("coop", "modern-v1"))
    records = read_scores(ctx.store.path)[0]
    assert [(r.name, r.score, r.mode, r.level) for r in records] == [("Team", 17, "coop", 4)]
    screen.handle_events([key(pygame.K_RETURN)])
    assert len(read_scores(ctx.store.path)[0]) == 1


def test_name_is_limited_to_24_characters(ctx):
    screen = GameOverScreen(ctx, result())
    screen.handle_events([key(0, "x") for _ in range(40)])
    assert len(screen.name) == 24


def test_save_failure_offers_retry_and_continue(ctx, monkeypatch):
    screen = GameOverScreen(ctx, result())
    calls = []

    def failing(record):
        calls.append(record)
        raise OSError("disk full")
    monkeypatch.setattr(ctx.store, "save", failing)
    assert type_name(screen, "Ada") is None and "disk full" in screen.error
    monkeypatch.undo()
    t = screen.handle_events([key(pygame.K_r)])                # retry reuses the pending result and name
    assert t.target == "scores" and [r.name for r in read_scores(ctx.store.path)[0]] == ["Ada"]
    assert calls[0].run_id == "run-1"

    other = GameOverScreen(ctx, result(run_id="run-2"))
    monkeypatch.setattr(ctx.store, "save", failing)
    type_name(other, "Bo")
    t = other.handle_events([key(pygame.K_c)])
    assert t.target == "scores" and "not saved" in t.notice


def test_scores_screen_top10_and_buckets(ctx, surface):
    for i in range(12):
        ctx.store.save(ScoreRecord(f"s{i}", f"p{i}", i, "solo", 1, "modern-v1"))
    ctx.store.save(ScoreRecord("c1", "team", 50, "coop", 2, "modern-v1"))
    screen = ScoresScreen(ctx, ("solo", "modern-v1"))
    assert [r.score for r in screen.rows()] == list(range(11, 1, -1))
    screen.handle_events([key(pygame.K_RIGHT)])
    assert [r.name for r in screen.rows()] == ["team"]
    screen.draw(surface)
    assert screen.handle_events([key(pygame.K_ESCAPE)]).target == "menu"


def test_scores_screen_reports_unreadable_file(ctx, surface):
    ctx.store.path.parent.mkdir(parents=True)
    ctx.store.path.write_bytes(b"not,a,score,file\n")
    screen = ScoresScreen(ctx)
    assert screen.error and screen.rows() == []
    screen.draw(surface)


def test_settings_adjust_and_persist(ctx):
    ctx.assets.music_path = object()                        # pretend audio is available
    screen = SettingsScreen(ctx)
    screen.handle_events([key(pygame.K_RIGHT)] * 3)
    screen.handle_events([key(pygame.K_DOWN), key(pygame.K_LEFT), key(pygame.K_DOWN), key(pygame.K_RETURN)])
    t = screen.handle_events([key(pygame.K_ESCAPE)])
    assert t.target == "menu" and not t.notice
    from space_invaders import preferences
    saved, _ = preferences.load(ctx.preferences_path)
    assert saved == Preferences(0.085, 0.9, True)


def test_settings_without_audio_disable_volume(ctx, surface):
    screen = SettingsScreen(ctx)
    screen.handle_events([key(pygame.K_RIGHT)])
    assert ctx.preferences.music_volume == Preferences().music_volume
    assert "unavailable" in screen.label("Music volume")
    screen.draw(surface)


def test_settings_save_error_is_reported(ctx, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    ctx.preferences_path = blocker / "settings.json"
    t = SettingsScreen(ctx).handle_events([key(pygame.K_ESCAPE)])
    assert t.target == "menu" and "not saved" in t.notice


@pytest.mark.parametrize("make", [
    lambda c: MenuScreen(c, "notice"), lambda c: InstructionsScreen(c, "coop"),
    lambda c: GameplayScreen(c, "coop", random.Random(1)), lambda c: GameOverScreen(c, result("coop")),
    lambda c: ScoresScreen(c), lambda c: SettingsScreen(c),
    lambda c: PauseScreen(c, GameplayScreen(c, "solo", random.Random(1))),
])
def test_every_screen_draws(ctx, surface, make):
    make(ctx).draw(surface)


def test_effects_are_bounded_and_do_not_touch_gameplay_rng(ctx):
    a = GameplayScreen(ctx, "solo", random.Random(9))
    ctx.preferences = Preferences(reduced_effects=True)
    b = GameplayScreen(ctx, "solo", random.Random(9))
    for screen in (a, b):
        for _ in range(300):
            screen.update(1 / 60)
    assert a.session.rng.getstate() == b.session.rng.getstate()
    from space_invaders.gameplay import Feedback
    for _ in range(40):
        a.effects.add(Feedback("kill", 10, 10))
    assert len(a.effects.particles) == 96
    b.effects.add(Feedback("kill", 10, 10))
    assert b.effects.particles == []
    a.effects.update(1.0)
    assert a.effects.particles == [] and a.effects.flashes == {}


def test_scores_after_unreadable_legacy_does_not_crash(ctx, tmp_path, surface, monkeypatch):
    legacy = tmp_path / "legacy" / "scores.txt"
    legacy.parent.mkdir()
    legacy.write_bytes(b"(old, 9)\n")
    ctx.store = ScoreStore(tmp_path / "data2", legacy)
    from pathlib import Path
    real = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes",
                        lambda self: (_ for _ in ()).throw(PermissionError("denied")) if self == legacy else real(self))
    screen = GameOverScreen(ctx, result())
    type_name(screen, "Ada")
    assert screen.error
    t = screen.handle_events([key(pygame.K_c)])
    scores = ScoresScreen(ctx, t.bucket, t.notice)
    assert "denied" in scores.error
    scores.draw(surface)


def test_save_reports_migration_notice(ctx, tmp_path):
    legacy = tmp_path / "legacy" / "scores.txt"
    legacy.parent.mkdir()
    legacy.write_bytes(b"(old, 9)\nbroken\n")
    ctx.store = ScoreStore(tmp_path / "data2", legacy)
    t = type_name(GameOverScreen(ctx, result()), "Ada")
    assert "skipped" in t.notice


@pytest.mark.parametrize("center_x,top", [(-50, 400), (2000, 400), (475, -30), (475, 900)])
def test_status_text_stays_inside_viewport(ctx, center_x, top):
    from space_invaders.screens import clamped_text_pos
    text = ctx.fonts["small"].render("OVERHEATED - release fire to cool", True, (255, 255, 255))
    x, y = clamped_text_pos(text, center_x, top)
    assert 0 <= x and x + text.get_width() <= 950 and 0 <= y and y + text.get_height() <= 750
