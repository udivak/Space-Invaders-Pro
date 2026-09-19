"""Whole-session invariants, determinism and fixed-step timing."""
import random
from types import SimpleNamespace

import pytest

from space_invaders.gameplay import GameSession, PlayerAction
from space_invaders.preferences import Preferences
from space_invaders.screens import GameplayScreen
from space_invaders.settings import BALANCE


def scripted_actions(seed, players, ticks):
    rng = random.Random(seed)
    return [[PlayerAction(rng.choice((-1, 0, 1)), rng.choice((-1, 0, 1)), rng.random() < 0.7)
             for _ in range(players)] for _ in range(ticks)]


def snapshot(s):
    return (s.level, s.invasions, s.boss_bonus_total, s.defeat_reason,
            [(round(p.x, 3), round(p.y, 3), p.health, round(p.heat, 3), p.kills, p.cool_down_counter,
              p.triple_ticks, p.shield_charges, len(p.lasers)) for p in s.players],
            [(type(e).__name__, round(e.x, 3), round(e.y, 3), e.health, len(e.lasers)) for e in s.enemies],
            [(round(k.x, 3), round(k.y, 3), k.kind) for k in s.packages])


@pytest.mark.parametrize("mode,players", [("solo", 1), ("coop", 2)])
def test_seeded_sessions_are_deterministic_and_keep_invariants(images, mode, players):
    runs = []
    for _ in range(2):
        s = GameSession(mode, images, random.Random(11))
        for actions in scripted_actions(5, players, 3000):
            s.update_step(actions)
            assert len(s.packages) <= 1
            for p in s.players:
                assert 0 <= p.heat <= BALANCE.heat_capacity
                assert p.health <= 100 and 0 <= p.shield_charges <= 3 and 0 <= p.triple_ticks <= 720
            assert s.invasions <= 5
            if s.defeated:
                break
        runs.append(snapshot(s))
    assert runs[0] == runs[1]


def test_frozen_session_does_not_change_after_defeat(images):
    s = GameSession("solo", images, random.Random(1))
    s.update_step()
    s.invasions = 0
    s.update_step()
    assert s.defeated
    before = snapshot(s)
    for _ in range(100):
        s.update_step([PlayerAction(1, 0, True)])
    assert snapshot(s) == before


def test_feedback_is_drained_once(images):
    s = GameSession("solo", images, random.Random(1))
    s.update_step([PlayerAction(fire=True)])
    assert [f.kind for f in s.drain_feedback()] == ["shot"]
    assert s.drain_feedback() == []


# -- fixed-step timing (Task 3.2) -------------------------------------------------
class _Assets:
    images = None

    def __init__(self, images):
        self.images = images

    def start_music(self, volume):
        pass

    play = resume_music = pause_music = stop_music = lambda *a: None


def gameplay_screen(images, seed=3, fire=True):
    class Keys(dict):
        def __missing__(self, key):
            return key == 32 and fire         # K_SPACE held

    ctx = SimpleNamespace(assets=_Assets(images), preferences=Preferences(), key_state=lambda: Keys())
    return GameplayScreen(ctx, "solo", random.Random(seed))


@pytest.mark.parametrize("fps", [30, 60, 120])
def test_render_rate_does_not_change_simulation(images, fps):
    reference = gameplay_screen(images)
    for _ in range(600):
        reference.update(1 / 60)
    screen = gameplay_screen(images)
    for _ in range(fps * 10):
        screen.update(1 / fps)
    assert screen.session.ticks == reference.session.ticks == 600
    assert snapshot(screen.session) == snapshot(reference.session)


def test_stall_is_capped(images):
    screen = gameplay_screen(images)
    screen.update(5.0)
    assert screen.session.ticks == 15
    screen.update(0.5)
    assert screen.session.ticks == 30
    screen.update(0.0)
    assert screen.session.ticks == 30


def test_resume_discards_accumulated_time(images):
    screen = gameplay_screen(images)
    screen.update(0.01)
    screen.on_resume()
    assert screen.accumulator == 0.0
