"""Named constants, gameplay tuning and control bindings.

Units are explicit: ``_px_per_tick`` values apply once per 60-Hz simulation tick.
"""
from dataclasses import dataclass

import pygame

WIDTH, HEIGHT = 950, 750
RENDER_FPS = 60
SIM_HZ = 60
MAX_FRAME_SECONDS = 0.25
MAX_STEPS_PER_FRAME = 15
TITLE = "Space Invaders Pro"

# Current gameplay rules. Each Phase 5 rule change used its own identifier so that
# stored results stay grouped by the rules that produced them.
RULESET = "modern-v1"

# UI colors
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREY = (100, 100, 100)
FOCUS = (160, 160, 200)
DISABLED = (70, 70, 70)
P1_COLOR = (65, 105, 255)
P2_COLOR = (255, 140, 0)
GAME_OVER_COLOR = (0, 170, 255)
HEALTH_BACK = (255, 0, 0)
HEALTH_FRONT = (0, 255, 170)
BOSS_HEALTH_FRONT = (150, 0, 210)
HEAT_COLOR = (255, 125, 0)
SHIELD_RING = (169, 169, 169)
WARNING_COLOR = (255, 80, 80)

# Font sizes (pygame's bundled default font)
TITLE_FONT_SIZE = 44
BODY_FONT_SIZE = 30
HUD_FONT_SIZE = 30
BIG_FONT_SIZE = 80

GAME_OVER_SECONDS = 1.5


@dataclass(frozen=True)
class Balance:
    player_speed_px_per_tick: float = 7.4
    player_health: int = 100
    shot_cooldown_ticks: int = 17
    heat_capacity: float = 88.0
    heat_per_shot_tick: float = 0.45
    heat_per_triple_tick: float = 0.35
    heat_cooling_per_tick: float = 0.6
    laser_speed_px_per_tick: float = 10.5
    triple_side_slope: float = 0.4
    enemy_speed_px_per_tick: float = 1.0
    package_speed_px_per_tick: float = 1.4
    bullet_damage: int = 10
    contact_damage: int = 15
    boss_hit_damage: int = 28
    boss_health: int = 400
    boss_speed_px_per_tick: float = 1.75
    boss_amplitude_px: float = 100.0
    boss_phase_per_tick: float = 1.75 * 0.03
    wave_base: int = 10
    wave_increment_solo: int = 2
    wave_increment_coop: int = 5
    max_invasions: int = 5
    wave_heal: int = 20
    enemy_shot_chance: int = 70          # one attempt of 1/70 per tick
    kill_points: int = 1
    boss_bonus: int = 10
    # Phase 5 rules
    spawn_interval_ticks: int = 45
    spawn_lanes: int = 6
    spawn_x_min: int = 50
    spawn_x_max: int = 850
    boss_warning_ticks: int = 60
    weave_amplitude_px: float = 40.0
    weave_phase_per_tick: float = 1 / 60
    boss_phase1_interval_ticks: int = 72
    boss_phase2_interval_ticks: int = 96
    boss_telegraph_ticks: int = 15
    triple_duration_ticks: int = 720
    shield_charges: int = 3


BALANCE = Balance()


@dataclass(frozen=True)
class ControlBindings:
    left: int
    right: int
    up: int
    down: int
    fire: int


SOLO_CONTROLS = ControlBindings(pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_SPACE)
COOP_P1_CONTROLS = ControlBindings(pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_l)
COOP_P2_CONTROLS = ControlBindings(pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_g)


def bindings_for(mode):
    return [SOLO_CONTROLS] if mode == "solo" else [COOP_P1_CONTROLS, COOP_P2_CONTROLS]
