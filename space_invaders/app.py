"""Application startup, the single frame loop and shutdown."""
import os
import sys
from dataclasses import dataclass, field

import pygame

from space_invaders import assets as assets_module
from space_invaders import paths
from space_invaders import preferences as prefs_module
from space_invaders.scores import LEGACY_ENCODING_ENV, MigrationError, ScoreStore
from space_invaders.screens import (GameOverScreen, GameplayScreen, InstructionsScreen, MenuScreen, PauseScreen,
                                    ScoresScreen, SettingsScreen, Transition)
from space_invaders.settings import (BIG_FONT_SIZE, BODY_FONT_SIZE, HEIGHT, HUD_FONT_SIZE, RENDER_FPS, TITLE,
                                     TITLE_FONT_SIZE, WIDTH)


@dataclass
class Context:
    """Shared, explicitly constructed resources handed to screens."""
    assets: object
    fonts: dict
    store: ScoreStore
    preferences: prefs_module.Preferences
    preferences_path: object
    key_state: object = field(default=pygame.key.get_pressed)
    rng_factory: object = None


def make_fonts():
    return {"title": pygame.font.Font(None, TITLE_FONT_SIZE), "body": pygame.font.Font(None, BODY_FONT_SIZE),
            "hud": pygame.font.Font(None, HUD_FONT_SIZE), "big": pygame.font.Font(None, BIG_FONT_SIZE),
            "small": pygame.font.Font(None, 24)}


class App:
    def __init__(self, ctx, notice=""):
        self.ctx = ctx
        self.screen = MenuScreen(ctx, notice)
        self.running = True
        self.focused = True

    def build(self, transition):
        t, ctx = transition.target, self.ctx
        if t == "menu":
            return MenuScreen(ctx, transition.notice)
        if t == "instructions":
            return InstructionsScreen(ctx, transition.mode)
        if t == "gameplay":
            rng = ctx.rng_factory() if ctx.rng_factory else None
            return GameplayScreen(ctx, transition.mode, rng)
        if t == "pause":
            return PauseScreen(ctx, transition.screen)
        if t == "resume":
            transition.screen.on_resume()
            return transition.screen
        if t == "game_over":
            return GameOverScreen(ctx, transition.result)
        if t == "scores":
            return ScoresScreen(ctx, transition.bucket, transition.notice)
        if t == "settings":
            return SettingsScreen(ctx)
        raise ValueError(f"unknown transition {t!r}")

    def step(self, events, elapsed):
        """One frame: QUIT first, events once, update, at most one transition. Returns False to stop."""
        if any(event.type == pygame.QUIT for event in events):
            self.running = False
            return False
        for event in events:               # focus is tracked globally, independent of screen input
            if event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
        transition = self.screen.handle_events(events)   # remainder of the batch is discarded on transition
        if transition is None and self._must_pause():
            transition = Transition("pause", screen=self.screen)
        if transition is None:
            transition = self.screen.update(elapsed)
        if transition is not None:
            if transition.target == "quit":
                self.running = False
                return False
            self.screen = self.build(transition)
            if self._must_pause():         # never start or resume a run while the window is unfocused
                self.screen = self.build(Transition("pause", screen=self.screen))
        return True

    def _must_pause(self):
        return (not self.focused and isinstance(self.screen, GameplayScreen)
                and not self.screen.session.defeated)

    def draw(self, surface):
        self.screen.draw(surface)


def _startup(environ):
    """Create display, audio, assets, fonts, data locations and preferences. Returns (surface, ctx, notice)."""
    data_dir = paths.data_dir(environ)
    pygame.display.init()
    pygame.font.init()
    audio = assets_module.init_audio()
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    bundle = assets_module.load_assets(paths.resource_root(), audio)
    pygame.display.set_icon(bundle.images["player"])
    preferences_path = data_dir / "settings.json"
    preferences, notice = prefs_module.load(preferences_path)
    bundle.set_effects_volume(preferences.effects_volume)
    legacy = None if paths.is_frozen() else paths.legacy_scores_path()
    store = ScoreStore(data_dir, legacy, environ.get(LEGACY_ENCODING_ENV))
    try:
        store.migrate()
        notice = notice or store.migration_notice()
    except MigrationError as error:
        notice = notice or str(error)
    ctx = Context(bundle, make_fonts(), store, preferences, preferences_path)
    return surface, ctx, notice


def run(environ=None):
    environ = os.environ if environ is None else environ
    try:
        try:
            surface, ctx, notice = _startup(environ)
        except (ValueError, assets_module.AssetError) as error:
            print(f"space_invaders: {error}", file=sys.stderr)
            return 2
        app = App(ctx, notice)
        clock = pygame.time.Clock()
        while app.running:
            elapsed = clock.tick(RENDER_FPS) / 1000.0
            if not app.step(pygame.event.get(), elapsed):
                break
            app.draw(surface)
            pygame.display.flip()
        return 0
    finally:
        pygame.quit()
