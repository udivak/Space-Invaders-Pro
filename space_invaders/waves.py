"""Deterministic wave and package spawn specifications. All randomness comes from the passed RNG."""
from dataclasses import dataclass

from space_invaders.entities import Enemy, Package
from space_invaders.settings import BALANCE, WIDTH


@dataclass(frozen=True)
class SpawnSpec:
    tick: int
    kind: str          # "enemy" or "boss"
    x: float
    y: float
    color: str = ""


def wave_count(level, mode, balance=BALANCE):
    increment = balance.wave_increment_coop if mode == "coop" else balance.wave_increment_solo
    return balance.wave_base + increment * level


def is_boss_level(level):
    return level >= 3 and level % 2 == 1


def lane_positions(balance=BALANCE):
    step = (balance.spawn_x_max - balance.spawn_x_min) / (balance.spawn_lanes - 1)
    return [balance.spawn_x_min + i * step for i in range(balance.spawn_lanes)]


def lane_sequence(count, rng, balance=BALANCE):
    """Lanes shuffled per batch of six, never repeating a lane across a batch boundary."""
    lanes = lane_positions(balance)
    sequence = []
    while len(sequence) < count:
        batch = lanes[:]
        rng.shuffle(batch)
        if sequence and batch[0] == sequence[-1]:
            batch[0], batch[-1] = batch[-1], batch[0]
        sequence.extend(batch)
    return sequence[:count]


def build_wave(level, mode, rng, enemy_height, balance=BALANCE):
    """Return the spawn schedule for a wave, ordered by tick."""
    count = wave_count(level, mode, balance)
    specs = [SpawnSpec(i * balance.spawn_interval_ticks, "enemy", x, -enemy_height, rng.choice(Enemy.COLORS))
             for i, x in enumerate(lane_sequence(count, rng, balance))]
    if is_boss_level(level):
        boss = SpawnSpec(balance.boss_warning_ticks, "boss",
                         rng.randrange(int(WIDTH * 0.25), int(WIDTH * 0.75)), rng.randrange(100, 300))
        specs.append(boss)
        specs.sort(key=lambda spec: spec.tick)
    return specs


def package_spec(rng):
    """Classic package placement: x=50..849, y=-500..-101, random type."""
    return (rng.randrange(50, WIDTH - 100), rng.randrange(-500, -100), rng.choice(Package.TYPES))
