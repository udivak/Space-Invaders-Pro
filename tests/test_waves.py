import random

import pytest

from conftest import ScriptedRandom
from space_invaders import waves
from space_invaders.gameplay import GameSession


@pytest.mark.parametrize("level", range(1, 11))
def test_wave_counts(level):
    assert waves.wave_count(level, "solo") == 10 + 2 * level
    assert waves.wave_count(level, "coop") == 10 + 5 * level


def test_boss_levels():
    assert [lvl for lvl in range(1, 11) if waves.is_boss_level(lvl)] == [3, 5, 7, 9]


def test_lanes_span_classic_range():
    assert waves.lane_positions() == [50, 210, 370, 530, 690, 850]


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("mode", ["solo", "coop"])
def test_schedule(seed, mode):
    for level in (1, 3, 4):
        specs = waves.build_wave(level, mode, random.Random(seed), 50)
        enemies = [s for s in specs if s.kind == "enemy"]
        assert len(enemies) == waves.wave_count(level, mode)
        assert [s.tick for s in enemies] == [i * 45 for i in range(len(enemies))]
        assert all(s.y == -50 and 50 <= s.x <= 850 for s in enemies)
        lanes = [s.x for s in enemies]
        assert all(a != b for a, b in zip(lanes, lanes[1:]))       # never the same lane twice in a row
        for start in range(0, len(lanes) - 5, 6):
            assert len(set(lanes[start:start + 6])) == 6
        bosses = [s for s in specs if s.kind == "boss"]
        if waves.is_boss_level(level):
            assert len(bosses) == 1 and bosses[0].tick == 60
            assert 237 <= bosses[0].x < 712 and 100 <= bosses[0].y < 300
        else:
            assert bosses == []


def test_same_seed_same_sequence():
    a = waves.build_wave(5, "coop", random.Random(7), 50)
    b = waves.build_wave(5, "coop", random.Random(7), 50)
    assert a == b


def test_package_spec_bounds():
    rng = random.Random(3)
    for _ in range(200):
        x, y, kind = waves.package_spec(rng)
        assert 50 <= x <= 849 and -500 <= y <= -101 and kind in ("hp", "triple_laser", "shield")


def test_pending_spawns_prevent_early_wave_clear(images):
    s = GameSession("solo", images, ScriptedRandom(2))
    s.update_step()
    assert s.level == 1 and len(s.enemies) == 1 and len(s.pending) == 11
    while s.pending:                      # every visible enemy is destroyed immediately
        s.enemies.clear()
        s.update_step()
        assert s.level == 1               # the wave never clears while spawns are pending
    s.enemies.clear()
    s.update_step()
    assert s.level == 2


def test_last_ordinary_spawn_tick(images):
    s = GameSession("solo", images, ScriptedRandom(2))
    spawned_at = []
    for tick in range(12 * 45):
        before = len(s.enemies)
        s.update_step()
        if len(s.enemies) > before:
            spawned_at.append(tick)
        for e in s.enemies:
            e.y = -200                    # keep them off-screen
    assert spawned_at[0] == 0 and spawned_at[-1] == 11 * 45 and len(spawned_at) == 12


def test_boss_warning_then_boss_at_tick_60(images):
    s = GameSession("solo", images, ScriptedRandom(4))
    s.level = 2
    s.update_step()                       # starts level 3
    assert s.level == 3 and s.boss_incoming and s.boss is None
    for _ in range(59):
        s.update_step()
    assert s.boss is None                 # ticks 0..59: warning only; cannot collide or fire
    s.update_step()                       # tick 60
    assert s.boss is not None and not s.boss_incoming


def test_wave_recovery(images):
    s = GameSession("coop", images, ScriptedRandom(5))
    s.update_step()
    s.pending.clear()
    s.enemies.clear()
    s.invasions = 3
    s.players[0].health, s.players[1].health = 50, 90
    s.update_step()
    assert s.level == 2 and s.invasions == 4
    assert [p.health for p in s.players] == [70, 100]


def test_no_recovery_or_spawn_after_defeat(images):
    s = GameSession("solo", images, ScriptedRandom(5))
    s.update_step()
    s.pending.clear()
    s.enemies.clear()
    s.players[0].health = -5                   # death and wave completion coincide
    s._check_defeat()
    s.update_step()
    assert s.defeated and s.level == 1 and s.players[0].health == -5 and s.enemies == []
