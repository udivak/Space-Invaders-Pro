"""Concrete screens. Each exposes handle_events(events), update(elapsed_seconds) and draw(surface).

Screens never read the event queue, tick a clock, present the display or call another screen;
they return a Transition that the App applies.
"""
import random
import unicodedata
from dataclasses import dataclass, replace

import pygame

from space_invaders import preferences as prefs_module
from space_invaders.gameplay import GameSession, PlayerAction
from space_invaders.scores import (MigrationError, ScoreFileError, ScoreRecord, buckets, rank,
                                   sanitize_name, NAME_LIMIT)
from space_invaders.settings import (DISABLED, FOCUS, GAME_OVER_COLOR, GAME_OVER_SECONDS, GREY,
                                     HEALTH_BACK, BOSS_HEALTH_FRONT, HEIGHT, MAX_FRAME_SECONDS,
                                     MAX_STEPS_PER_FRAME, P1_COLOR, P2_COLOR, RULESET, SIM_HZ, WARNING_COLOR,
                                     WHITE, WIDTH, YELLOW, bindings_for)

SIM_DT = 1.0 / SIM_HZ
DEFEAT_TEXT = {"health": "A ship was destroyed", "breaches": "Too many enemies broke through",
               "boss_contact": "Collided with the boss"}
MODE_LABEL = {"solo": "Solo", "coop": "Co-op", "legacy": "Legacy"}


@dataclass(frozen=True)
class Transition:
    target: str                 # menu, instructions, gameplay, pause, resume, game_over, scores, settings, quit
    mode: str = None
    result: object = None
    screen: object = None
    bucket: tuple = None
    notice: str = ""


def blit_center(surface, text_surface, y, x=WIDTH / 2):
    surface.blit(text_surface, (x - text_surface.get_width() / 2, y))


def displayable(text):
    """Replace control characters (pygame cannot render NUL) without altering stored data."""
    return "".join("?" if unicodedata.category(ch) == "Cc" else ch for ch in text)


def shorten(text, limit=NAME_LIMIT):
    text = displayable(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


class ButtonList:
    """Vertical list of buttons with keyboard focus, hover and click activation."""
    WIDTH, HEIGHT, GAP = 260, 50, 14

    def __init__(self, labels, top):
        self.labels = labels
        self.top = top
        self.focus = 0
        self.disabled = set()

    def rect(self, index):
        return pygame.Rect(WIDTH // 2 - self.WIDTH // 2, self.top + index * (self.HEIGHT + self.GAP),
                           self.WIDTH, self.HEIGHT)

    def index_at(self, pos):
        return next((i for i in range(len(self.labels)) if self.rect(i).collidepoint(pos)), None)

    def handle(self, event):
        """Return the activated label, or None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_TAB) and not (event.key == pygame.K_TAB and event.mod & pygame.KMOD_SHIFT):
                self.focus = (self.focus + 1) % len(self.labels)
            elif event.key in (pygame.K_UP, pygame.K_TAB):
                self.focus = (self.focus - 1) % len(self.labels)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._activate(self.focus)
        elif event.type == pygame.MOUSEMOTION:
            index = self.index_at(event.pos)
            if index is not None:
                self.focus = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.index_at(event.pos)
            if index is not None:
                self.focus = index
                return self._activate(index)
        return None

    def _activate(self, index):
        label = self.labels[index]
        return None if label in self.disabled else label

    def draw(self, surface, font):
        for i, label in enumerate(self.labels):
            rect = self.rect(i)
            color = DISABLED if label in self.disabled else (FOCUS if i == self.focus else GREY)
            pygame.draw.rect(surface, color, rect)
            if i == self.focus:
                pygame.draw.rect(surface, WHITE, rect, 2)
            text = font.render(label, True, WHITE)
            surface.blit(text, (rect.centerx - text.get_width() / 2, rect.centery - text.get_height() / 2))


class MenuScreen:
    def __init__(self, ctx, notice=""):
        self.ctx = ctx
        self.notice = notice
        self.buttons = ButtonList(["1 Player", "2 Players", "Scores", "Settings", "Quit"], 330)

    def handle_events(self, events):
        for event in events:
            choice = self.buttons.handle(event)
            if choice == "1 Player":
                return Transition("instructions", mode="solo")
            if choice == "2 Players":
                return Transition("instructions", mode="coop")
            if choice == "Scores":
                return Transition("scores")
            if choice == "Settings":
                return Transition("settings")
            if choice == "Quit":
                return Transition("quit")
        return None

    def update(self, elapsed):
        return None

    def draw(self, surface):
        fonts = self.ctx.fonts
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        blit_center(surface, fonts["title"].render("Welcome to Space Invaders Pro !!!", True, WHITE), 200)
        blit_center(surface, fonts["body"].render("Choose number of players...", True, WHITE), 270)
        self.buttons.draw(surface, fonts["body"])
        if self.notice:
            blit_center(surface, fonts["body"].render(shorten(self.notice, 80), True, WARNING_COLOR), HEIGHT - 60)


class InstructionsScreen:
    def __init__(self, ctx, mode):
        self.ctx = ctx
        self.mode = mode

    def lines(self):
        if self.mode == "solo":
            controls = [("Arrows move the ship, Space shoots", WHITE)]
        else:
            controls = [("Player 1 (blue): Arrows move, L shoots", P1_COLOR),
                        ("Player 2 (orange): W A S D move, G shoots", P2_COLOR)]
        rules = [
            "Destroy the enemies before they invade your planet!",
            "Holding fire builds heat; at full heat release fire to cool down.",
            "Each enemy that reaches the bottom costs a breach; 5 breaches allowed.",
            "Blue enemies weave side to side. Touching an enemy costs 15 health.",
            "Bosses appear on odd levels from 3. Touching a boss ends the run.",
            "Packs: health refill, triple shot for 12 s, shield blocks 3 shots.",
            "Enemy kill = 1 point, boss = 10 bonus. Esc pauses.",
        ]
        if self.mode == "coop":
            rules.append("Co-op: the run ends if either ship is destroyed; score is shared.")
        return controls + [(rule, WHITE) for rule in rules]

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return Transition("menu")
            if (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)) \
                    or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                return Transition("gameplay", mode=self.mode)
        return None

    def update(self, elapsed):
        return None

    def draw(self, surface):
        fonts = self.ctx.fonts
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        blit_center(surface, fonts["title"].render("How to play", True, YELLOW), 120)
        for i, (line, color) in enumerate(self.lines()):
            blit_center(surface, fonts["body"].render(line, True, color), 200 + i * 42)
        blit_center(surface, fonts["body"].render("Press Enter, Space or click to begin - Esc for menu", True, WHITE),
                    HEIGHT - 80)


class Effects:
    """Bounded decorative feedback. Uses its own RNG, never the gameplay RNG."""
    MAX_PARTICLES = 96
    FLASH_SECONDS = 0.08
    PARTICLE_SECONDS = 0.3
    TEXT_SECONDS = 1.0

    def __init__(self, reduced=False, rng=None):
        self.reduced = reduced
        self.rng = rng or random.Random()
        self.particles = []     # [x, y, vx, vy, remaining]
        self.flashes = {}       # id(entity) -> [entity, remaining]
        self.texts = []         # [text, x, y, remaining]

    def add(self, feedback):
        kind = feedback.kind
        if kind in ("hit", "player_hit", "shield_block"):
            self.flashes[id(feedback.target)] = [feedback.target, self.FLASH_SECONDS]
        if kind in ("kill", "boss_kill") and not self.reduced:
            for _ in range(6):
                self.particles.append([feedback.x, feedback.y + 20, self.rng.uniform(-120, 120),
                                       self.rng.uniform(-120, 120), self.PARTICLE_SECONDS])
            del self.particles[:-self.MAX_PARTICLES]
        if kind == "pickup":
            label = {"hp": "+Health", "shield": "+Shield", "triple_laser": "+Triple shot"}[feedback.target]
            self.texts.append([label, feedback.x, feedback.y - 30, self.TEXT_SECONDS])
        if kind == "expiry":
            self.texts.append(["Triple shot expired", feedback.x, feedback.y - 30, self.TEXT_SECONDS])

    def update(self, elapsed):
        for p in self.particles:
            p[0] += p[2] * elapsed
            p[1] += p[3] * elapsed
            p[4] -= elapsed
        self.particles = [p for p in self.particles if p[4] > 0]
        for key in list(self.flashes):
            self.flashes[key][1] -= elapsed
            if self.flashes[key][1] <= 0:
                del self.flashes[key]
        for t in self.texts:
            t[3] -= elapsed
        self.texts = [t for t in self.texts if t[3] > 0]

    def draw(self, surface, font):
        for entity, _ in self.flashes.values():
            overlay = entity.mask.to_surface(setcolor=(255, 255, 255, 170), unsetcolor=(0, 0, 0, 0))
            surface.blit(overlay, (entity.x, entity.y))
        for x, y, _, _, remaining in self.particles:
            pygame.draw.circle(surface, YELLOW, (int(x), int(y)), max(1, int(4 * remaining / self.PARTICLE_SECONDS)))
        for text, x, y, _ in self.texts:
            rendered = font.render(text, True, WHITE)
            surface.blit(rendered, (x - rendered.get_width() / 2, y))


class GameplayScreen:
    def __init__(self, ctx, mode, rng=None):
        self.ctx = ctx
        self.mode = mode
        self.session = GameSession(mode, ctx.assets.images, rng)
        self.bindings = bindings_for(mode)
        self.accumulator = 0.0
        self.ending_elapsed = 0.0
        self.effects = Effects(ctx.preferences.reduced_effects)
        ctx.assets.start_music(ctx.preferences.music_volume)

    def actions(self):
        keys = self.ctx.key_state()
        return [PlayerAction(keys[b.right] - keys[b.left], keys[b.down] - keys[b.up], bool(keys[b.fire]))
                for b in self.bindings]

    def handle_events(self, events):
        if self.session.defeated:
            return None
        for event in events:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or event.type == pygame.WINDOWFOCUSLOST:
                return Transition("pause", screen=self)
        return None

    def on_resume(self):
        self.accumulator = 0.0
        self.ctx.assets.resume_music()

    def update(self, elapsed):
        elapsed = min(max(elapsed, 0.0), MAX_FRAME_SECONDS)
        if self.session.defeated:
            self.effects.update(elapsed)
            self.ending_elapsed += elapsed
            if self.ending_elapsed >= GAME_OVER_SECONDS:
                return Transition("game_over", result=self.session.result)
            return None
        self.accumulator += elapsed
        steps = 0
        while self.accumulator >= SIM_DT and steps < MAX_STEPS_PER_FRAME and not self.session.defeated:
            self.session.update_step(self.actions())
            self.accumulator -= SIM_DT
            steps += 1
        if steps == MAX_STEPS_PER_FRAME or self.session.defeated:
            self.accumulator = 0.0      # excess stall time is discarded, never replayed
        self.effects.update(elapsed)          # age old effects first so new ones survive their first draw
        for feedback in self.session.drain_feedback():
            if feedback.kind == "shot":
                self.ctx.assets.play("laser")
            elif feedback.kind == "boss_kill":
                self.ctx.assets.play("boss_explosion")
            self.effects.add(feedback)
        return None

    def draw(self, surface):
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        self.session.draw(surface)
        self.effects.draw(surface, self.ctx.fonts["small"])
        draw_hud(surface, self.ctx.fonts, self.session)
        if self.session.defeated:
            blit_center(surface, self.ctx.fonts["big"].render("Game Over !!!", True, GAME_OVER_COLOR), HEIGHT / 2 - 40)


def clamped_text_pos(text, center_x, top):
    """Top-left position for text centered on center_x, kept fully inside the viewport."""
    x = min(max(center_x - text.get_width() / 2, 0), WIDTH - text.get_width())
    y = min(max(top, 0), HEIGHT - text.get_height())
    return x, y


def draw_hud(surface, fonts, session):
    hud, small = fonts["hud"], fonts["small"]
    surface.blit(hud.render(f"Breaches left: {session.invasions}", True, (255, 0, 0)), (10, 10))
    level = hud.render(f"Level: {session.level}", True, WHITE)
    surface.blit(level, (WIDTH - level.get_width() - 10, 10))
    if session.mode == "coop":
        blit_center(surface, hud.render(f"Team score: {session.score}", True, WHITE), 10)
        p1, p2 = session.players
        blit_center(surface, small.render(f"P1 kills {p1.kills}  |  P2 kills {p2.kills}  |  boss bonus {session.boss_bonus_total}",
                                          True, WHITE), 38)
    else:
        blit_center(surface, hud.render(f"Score: {session.score}", True, P1_COLOR), 10)
    for player in session.players:
        color = P2_COLOR if player.player_id == 2 else P1_COLOR
        label = f"P{player.player_id} HP {max(0, player.health)}" if session.mode == "coop" else f"HP {max(0, player.health)}"
        parts = [label]
        if player.shield_active:
            parts.append(f"Shield x{player.shield_charges}")
        if player.triple_active:
            parts.append(f"Triple {player.triple_ticks / SIM_HZ:.0f}s")
        status = small.render("  ".join(parts), True, color)
        surface.blit(status, clamped_text_pos(status, player.x + player.width / 2, player.y + player.height + 28))
        if player.overheated:
            warn = small.render("OVERHEATED - release fire to cool", True, WARNING_COLOR)
            surface.blit(warn, clamped_text_pos(warn, player.x + player.width / 2, player.y - 22))
    boss = session.boss
    if boss is not None:
        bar = pygame.Rect(WIDTH / 2 - 150, 64, 300, 12)
        pygame.draw.rect(surface, HEALTH_BACK, bar)
        pygame.draw.rect(surface, BOSS_HEALTH_FRONT, (bar.x, bar.y, bar.width * boss.health / boss.max_health, bar.height))
        text = f"BOSS - phase {boss.attack_phase}" + ("  WARNING!" if boss.telegraphing else "")
        blit_center(surface, small.render(text, True, WARNING_COLOR if boss.telegraphing else WHITE), 80)
    elif session.boss_incoming:
        blit_center(surface, hud.render("Boss incoming!", True, WARNING_COLOR), 70)


class PauseScreen:
    def __init__(self, ctx, gameplay):
        self.ctx = ctx
        self.gameplay = gameplay
        self.buttons = ButtonList(["Resume", "Restart", "Menu", "Quit"], 330)
        ctx.assets.pause_music()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return Transition("resume", screen=self.gameplay)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                return Transition("gameplay", mode=self.gameplay.mode)
            choice = self.buttons.handle(event)
            if choice == "Resume":
                return Transition("resume", screen=self.gameplay)
            if choice == "Restart":
                return Transition("gameplay", mode=self.gameplay.mode)
            if choice == "Menu":
                self.ctx.assets.stop_music()
                return Transition("menu")
            if choice == "Quit":
                return Transition("quit")
        return None

    def update(self, elapsed):
        return None

    def draw(self, surface):
        self.gameplay.draw(surface)
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surface.blit(shade, (0, 0))
        blit_center(surface, self.ctx.fonts["title"].render("Paused", True, WHITE), 230)
        blit_center(surface, self.ctx.fonts["small"].render("Esc resumes, R restarts", True, WHITE), 280)
        self.buttons.draw(surface, self.ctx.fonts["body"])


class GameOverScreen:
    """Results, name entry and a single save with Retry / Continue on failure."""

    def __init__(self, ctx, result):
        self.ctx = ctx
        self.result = result
        self.name = ""
        self.error = ""
        self.saved = False

    def record(self):
        r = self.result
        return ScoreRecord(r.run_id, sanitize_name(self.name), r.score, r.mode, r.level, r.ruleset)

    def _scores(self, notice=""):
        return Transition("scores", bucket=(self.result.mode, self.result.ruleset), notice=notice)

    def _save(self):
        if not self.saved:
            try:
                self.ctx.store.save(self.record())
            except (OSError, ScoreFileError, MigrationError) as error:
                self.error = str(error)
                return None
            self.saved = True
        return self._scores(self.ctx.store.migration_notice())

    def handle_events(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self.error:
                if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.error = ""
                    transition = self._save()
                    if transition:
                        return transition
                elif event.key in (pygame.K_c, pygame.K_ESCAPE):
                    return self._scores("Score was not saved.")
                continue
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                transition = self._save()
                if transition:
                    return transition
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.name) < NAME_LIMIT:
                self.name += event.unicode
        return None

    def update(self, elapsed):
        return None

    def draw(self, surface):
        fonts, r = self.ctx.fonts, self.result
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        blit_center(surface, fonts["title"].render("Game Over", True, GAME_OVER_COLOR), 80)
        blit_center(surface, fonts["body"].render(DEFEAT_TEXT.get(r.defeat_reason, ""), True, WHITE), 140)
        lines = [f"{MODE_LABEL[r.mode]} score: {r.score}    Level reached: {r.level}"]
        if r.mode == "coop":
            lines.append(f"P1 kills: {r.kill_points[0]}    P2 kills: {r.kill_points[1]}    Boss bonus: {r.boss_bonus_total}")
        else:
            lines.append(f"Kills: {r.kill_points[0]}    Boss bonus: {r.boss_bonus_total}")
        for i, line in enumerate(lines):
            blit_center(surface, fonts["body"].render(line, True, WHITE), 200 + i * 40)
        blit_center(surface, fonts["body"].render("Enter your name:", True, WHITE), 320)
        box = pygame.Rect(WIDTH / 2 - 220, 360, 440, 44)
        pygame.draw.rect(surface, WHITE, box, 2)
        blit_center(surface, fonts["body"].render(self.name + "_", True, WHITE), 370)
        blit_center(surface, fonts["small"].render("Press Enter to save", True, WHITE), 420)
        if self.error:
            blit_center(surface, fonts["small"].render(shorten(f"Save failed: {self.error}", 90), True, WARNING_COLOR), 480)
            blit_center(surface, fonts["body"].render("R: retry    C: continue without saving", True, WHITE), 520)


class ScoresScreen:
    """Top 10 per (mode, ruleset); Left/Right switch between result groups, including Legacy."""

    def __init__(self, ctx, bucket=None, notice=""):
        self.ctx = ctx
        self.notices = [notice] if notice else []
        self.error = ""
        self.records = []
        try:
            self.records, warnings = ctx.store.load()
            self.notices += warnings
        except ScoreFileError as error:
            self.error = str(error)
        self.buckets = buckets(self.records)
        default = bucket or ("solo", RULESET)
        if default not in self.buckets:
            self.buckets.insert(0, default)
        self.index = self.buckets.index(default)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.index = (self.index - 1) % len(self.buckets)
                elif event.key == pygame.K_RIGHT:
                    self.index = (self.index + 1) % len(self.buckets)
                elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return Transition("menu")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                return Transition("menu")
        return None

    def update(self, elapsed):
        return None

    def rows(self):
        mode, ruleset = self.buckets[self.index]
        return rank(self.records, mode, ruleset)

    def draw(self, surface):
        fonts = self.ctx.fonts
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        mode, ruleset = self.buckets[self.index]
        title = "Legacy scores (imported history)" if mode == "legacy" else f"Top 10 - {MODE_LABEL[mode]} ({ruleset})"
        blit_center(surface, fonts["title"].render(title, True, YELLOW), 50)
        blit_center(surface, fonts["small"].render(f"< Left / Right: {self.index + 1} of {len(self.buckets)} >", True, WHITE), 100)
        if self.error:
            blit_center(surface, fonts["small"].render(shorten(f"Cannot read scores: {self.error}", 100), True, WARNING_COLOR), 140)
        rows = self.rows()
        if not rows and not self.error:
            blit_center(surface, fonts["body"].render("No scores saved yet.", True, WHITE), 250)
        for i, record in enumerate(rows):
            y = 150 + i * 42
            level = "?" if record.level == "unknown" else record.level
            surface.blit(fonts["body"].render(f"{i + 1}.", True, WHITE), (180, y))
            surface.blit(fonts["body"].render(shorten(record.name) or "(no name)", True, WHITE), (230, y))
            surface.blit(fonts["body"].render(str(record.score), True, WHITE), (600, y))
            surface.blit(fonts["body"].render(f"L{level}", True, WHITE), (700, y))
        for i, notice in enumerate(self.notices[:3]):
            blit_center(surface, fonts["small"].render(shorten(notice, 100), True, WARNING_COLOR), HEIGHT - 150 + i * 24)
        blit_center(surface, fonts["body"].render("Press Enter, Esc or click to return to menu", True, WHITE), HEIGHT - 60)


class SettingsScreen:
    ITEMS = ("Music volume", "Effects volume", "Reduced effects", "Back")
    STEPS = {"Music volume": 0.01, "Effects volume": 0.1}

    def __init__(self, ctx):
        self.ctx = ctx
        self.focus = 0
        self.notice = ""

    @property
    def audio(self):
        return self.ctx.assets.audio_enabled

    def _set(self, preferences):
        self.ctx.preferences = preferences
        self.ctx.assets.set_effects_volume(preferences.effects_volume)
        self.ctx.assets.set_music_volume(preferences.music_volume)

    def _adjust(self, direction):
        item, p = self.ITEMS[self.focus], self.ctx.preferences
        if item == "Reduced effects":
            self._set(replace(p, reduced_effects=not p.reduced_effects))
        elif item in self.STEPS and self.audio:
            field = "music_volume" if item == "Music volume" else "effects_volume"
            value = round(min(1.0, max(0.0, getattr(p, field) + direction * self.STEPS[item])), 3)
            self._set(replace(p, **{field: value}))

    def _leave(self):
        try:
            prefs_module.save(self.ctx.preferences_path, self.ctx.preferences)
        except OSError as error:
            return Transition("menu", notice=shorten(f"Settings not saved: {error}", 80))
        return Transition("menu")

    def handle_events(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    index = self.index_at(event.pos)
                    if index is not None:
                        self.focus = index
                        if self.ITEMS[index] == "Back":
                            return self._leave()
                        self._adjust(1 if event.button == 1 else -1)
                continue
            if event.key == pygame.K_ESCAPE:
                return self._leave()
            if event.key in (pygame.K_DOWN, pygame.K_TAB):
                self.focus = (self.focus + 1) % len(self.ITEMS)
            elif event.key == pygame.K_UP:
                self.focus = (self.focus - 1) % len(self.ITEMS)
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._adjust(1 if event.key == pygame.K_RIGHT else -1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.ITEMS[self.focus] == "Back":
                    return self._leave()
                self._adjust(1)
        return None

    def rect(self, index):
        return pygame.Rect(WIDTH // 2 - 250, 220 + index * 70, 500, 50)

    def index_at(self, pos):
        return next((i for i in range(len(self.ITEMS)) if self.rect(i).collidepoint(pos)), None)

    def update(self, elapsed):
        return None

    def label(self, item):
        p = self.ctx.preferences
        if item == "Music volume":
            return f"Music volume: {p.music_volume:.2f}" if self.audio else "Music volume: audio unavailable"
        if item == "Effects volume":
            return f"Effects volume: {p.effects_volume:.1f}" if self.audio else "Effects volume: audio unavailable"
        if item == "Reduced effects":
            return f"Reduced effects: {'on' if p.reduced_effects else 'off'}"
        return item

    def draw(self, surface):
        fonts = self.ctx.fonts
        surface.blit(self.ctx.assets.images["background"], (0, 0))
        blit_center(surface, fonts["title"].render("Settings", True, YELLOW), 120)
        for i, item in enumerate(self.ITEMS):
            rect = self.rect(i)
            disabled = item in self.STEPS and not self.audio
            pygame.draw.rect(surface, DISABLED if disabled else (FOCUS if i == self.focus else GREY), rect)
            if i == self.focus:
                pygame.draw.rect(surface, WHITE, rect, 2)
            text = fonts["body"].render(self.label(item), True, WHITE)
            surface.blit(text, (rect.centerx - text.get_width() / 2, rect.centery - text.get_height() / 2))
        blit_center(surface, fonts["small"].render("Up/Down select, Left/Right adjust, Enter toggles, Esc saves and returns",
                                                   True, WHITE), HEIGHT - 80)
