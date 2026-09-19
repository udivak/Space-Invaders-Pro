import math

import pytest

from space_invaders.entities import Boss, Enemy, Laser, Package, Player
from space_invaders.settings import BALANCE, HEIGHT, WIDTH


def test_laser_movement_and_offscreen(images):
    laser = Laser(0, 50, images["player_laser"])
    laser.move(10)
    assert laser.y == 60
    assert not laser.off_screen(100)
    laser.move(70)
    assert laser.off_screen(100)
    assert Laser(0, -1, images["player_laser"]).off_screen(HEIGHT)


def test_triple_side_lasers_use_slope(images):
    left = Laser(100, 100, images["player_laser"], True)
    right = Laser(100, 100, images["player_laser"], True, True)
    left.move(-10)
    right.move(-10)
    assert left.x == pytest.approx(96)
    assert right.x == pytest.approx(104)


def test_laser_collision(images):
    laser = Laser(0, 0, images["player_laser"])
    player = Player(0, 0, images)
    assert laser.collision(player)
    laser.move(200)
    assert not laser.collision(player)


def test_size_properties(images):
    player = Player(0, 0, images)
    assert (player.width, player.height) == images["player"].get_size()
    assert Package(0, 0, "shield", images).height == images["pack_shield"].get_height()


@pytest.mark.parametrize("player_id,ship,laser", [(1, "player", "player_laser"), (2, "player2", "player2_laser")])
def test_player_images(images, player_id, ship, laser):
    player = Player(0, 0, images, player_id)
    assert player.ship_img is images[ship] and player.laser_img is images[laser]


def test_fire_heat_cooldown_sequence(images):
    player = Player(400, 400, images)
    assert player.fire(True)
    assert len(player.lasers) == 1 and player.heat == pytest.approx(0.45)
    # Cooldown: counter set to 1, advanced by cooldown(); resets after reaching 17.
    fired = []
    for tick in range(40):
        player.cooldown()
        fired.append(player.fire(True))
    assert fired.index(True) == 16          # 17-tick cadence
    assert player.fire(False) is False
    assert player.heat == pytest.approx(0.45 * 41 - 0.6)


def test_heat_is_clamped_and_blocks_fire_until_released(images):
    player = Player(400, 400, images)
    for _ in range(400):
        player.cooldown()
        player.fire(True)
    assert player.heat == BALANCE.heat_capacity and player.overheated
    count = len(player.lasers)
    for _ in range(20):
        player.cooldown()
        assert player.fire(True) is False   # no cooling and no fire while held at full
    assert len(player.lasers) == count and player.heat == BALANCE.heat_capacity
    for _ in range(500):
        player.fire(False)
    assert player.heat == 0.0


def test_triple_shot_creates_three(images):
    player = Player(400, 400, images)
    player.triple_ticks = 10
    assert player.fire(True)
    assert len(player.lasers) == 3 and player.heat == pytest.approx(0.35)


@pytest.mark.parametrize("dx,dy,expected", [(1, 0, (407.4, 400)), (-1, 0, (392.6, 400)),
                                            (0, -1, (400, 392.6)), (0, 1, (400, 407.4)),
                                            (1, 1, (407.4, 407.4))])
def test_player_moves_per_axis(images, dx, dy, expected):
    player = Player(400, 400, images)
    player.move(dx, dy)
    assert (player.x, player.y) == pytest.approx(expected)


def test_player_movement_bounds(images):
    player = Player(WIDTH - 88 - 5, 3, images)
    player.move(1, -1)
    assert (player.x, player.y) == (WIDTH - 88 - 5, 3)
    player = Player(3, HEIGHT - 90 - 25, images)
    player.move(-1, 1)
    assert (player.x, player.y) == (3, HEIGHT - 90 - 25)


@pytest.mark.parametrize("color", ["red", "green"])
def test_straight_enemies(images, color):
    enemy = Enemy(100, 0, color, images)
    for _ in range(600):
        enemy.move(1)
    assert (enemy.x, enemy.y) == (100, 600)


def test_blue_enemy_weave(images):
    enemy = Enemy(850, 0, "blue", images)
    lane = enemy.lane_x
    assert lane == WIDTH - 70 - 40               # baseline clamped so the weave stays on screen
    xs = []
    for _ in range(600):
        enemy.move(1)
        xs.append(enemy.x)
    assert abs(xs[0] - lane) < 1                 # continuous first step
    assert min(xs) >= 0 and max(xs) + 70 <= WIDTH
    assert max(xs) - lane == pytest.approx(40, abs=0.1)
    assert enemy.y == 600                        # vertical distance unchanged
    for _ in range(round(4 * math.pi * 60) - 600):   # complete two full weave cycles
        enemy.move(1)
        xs.append(enemy.x)
    assert sum(xs) / len(xs) == pytest.approx(lane, abs=1)


def test_enemy_shoot_respects_cooldown(images):
    enemy = Enemy(0, 0, "red", images)
    assert enemy.shoot() and not enemy.shoot()
    assert len(enemy.lasers) == 1


@pytest.mark.parametrize("spawn_y", [100, 250, 299])
def test_boss_moves_continuously_around_spawn(images, spawn_y):
    boss = Boss(300, spawn_y, images)
    boss.move()
    assert abs(boss.y - spawn_y) <= 100 * 0.0525 + 1e-9
    assert boss.x == 301.75
    ys, prev = [], boss.y
    for _ in range(2000):                        # includes several x wraps
        boss.move()
        assert abs(boss.y - prev) <= 100 * 0.0525 + 1e-9   # no vertical teleport
        prev = boss.y
        ys.append(boss.y)
    assert max(ys) == pytest.approx(spawn_y + 100, abs=0.1)
    assert min(ys) == pytest.approx(spawn_y - 100, abs=0.1)
    assert all(y + boss.height > 0 and y < HEIGHT for y in ys)


def test_boss_x_wrap(images):
    boss = Boss(WIDTH, 200, images)
    boss.move()
    assert boss.x == 0


def _run_attack(boss, ticks):
    shots = []
    for tick in range(1, ticks + 1):
        n = boss.update_attack()
        if n:
            shots.append((tick, n))
    return shots


def test_boss_phase_one_fires_every_72_ticks(images):
    boss = Boss(300, 200, images)
    assert _run_attack(boss, 216) == [(72, 1), (144, 1), (216, 1)]


@pytest.mark.parametrize("health,phase", [(201, 1), (200, 2), (196, 2)])
def test_boss_phase_threshold(images, health, phase):
    boss = Boss(300, 200, images)
    boss.health = health
    boss.update_attack()
    assert boss.attack_phase == phase


def test_boss_phase_two_telegraph_and_volleys(images):
    boss = Boss(300, 200, images)
    _run_attack(boss, 70)                        # nearly due in phase one
    boss.health = 200
    shots = _run_attack(boss, 15 + 96 * 2)
    assert shots[0] == (15, 3)                   # announced volley after the 15-tick warning, not immediately
    assert shots == [(15, 3), (111, 3), (207, 3)]
    boss.health = 100
    _run_attack(boss, 10)
    assert boss.attack_phase == 2 and not boss.telegraphing   # transition happens once
    angled = [laser for laser in boss.lasers if laser.triple_flag]
    assert len(angled) == 6


def test_boss_does_not_fire_off_screen(images):
    boss = Boss(WIDTH + 10, 200, images)
    assert _run_attack(boss, 72) == []
    assert boss.lasers == []
