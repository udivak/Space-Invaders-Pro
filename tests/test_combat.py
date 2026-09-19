"""Projectile, contact and pickup resolution (B1-B6, B13) plus Phase 5 shield/triple/boss-bonus rules."""
import pytest

from conftest import ScriptedRandom
from space_invaders.entities import Boss, Enemy, Laser, Package
from space_invaders.gameplay import GameSession, PlayerAction
from space_invaders.settings import HEIGHT


def session(images, mode="solo"):
    s = GameSession(mode, images, ScriptedRandom(1))
    for i, p in enumerate(s.players):
        p.x, p.y = 400.0, 500.0     # overlapping players in co-op
    return s


# -- enemy projectiles ------------------------------------------------------------
@pytest.mark.parametrize("p1_shield", [0, 2])
def test_enemy_shot_hitting_both_players_is_consumed_once(images, p1_shield):     # B1
    s = session(images, "coop")
    p1, p2 = s.players
    p1.shield_charges = p1_shield
    enemy = Enemy(400, 100, "red", images)
    enemy.lasers.append(Laser(420, 470, enemy.laser_img))
    s._resolve_enemy_lasers(enemy)
    assert enemy.lasers == []
    assert p2.health == 100
    if p1_shield:
        assert p1.health == 100 and p1.shield_charges == p1_shield - 1
    else:
        assert p1.health == 90


def test_every_enemy_laser_moves_once(images):                                     # B5
    s = session(images)
    enemy = Enemy(0, 0, "red", images)
    gone = Laser(0, HEIGHT - 1, enemy.laser_img)          # leaves the screen this tick
    live = Laser(0, 10, enemy.laser_img)
    enemy.lasers[:] = [gone, live]
    s._resolve_enemy_lasers(enemy)
    assert enemy.lasers == [live] and live.y == 20.5


def test_every_player_laser_moves_once(images):                                    # B5
    s = session(images)
    p = s.players[0]
    gone = Laser(0, 5, p.laser_img)
    live = Laser(0, 300, p.laser_img)
    hit_first = Laser(700, 300, p.laser_img)
    after_hit = Laser(0, 400, p.laser_img)
    s.enemies = [Enemy(700, 250, "red", images)]
    p.lasers[:] = [gone, hit_first, live, after_hit]
    s._resolve_player_lasers(p)
    assert p.lasers == [live, after_hit]
    assert live.y == 289.5 and after_hit.y == 389.5


def test_player_shot_stops_at_first_target(images):                                # B6
    s = session(images)
    p = s.players[0]
    s.enemies = [Enemy(100, 100, c, images) for c in ("red", "green", "blue")]
    for e in s.enemies:
        e.x = 100
    p.lasers.append(Laser(100, 120, p.laser_img))
    s._resolve_player_lasers(p)
    assert len(s.enemies) == 2 and p.kills == 1 and p.lasers == []


def test_several_lasers_on_one_target(images):
    s = session(images)
    p = s.players[0]
    s.enemies = [Enemy(100, 100, "red", images)]
    p.lasers[:] = [Laser(100, 120, p.laser_img), Laser(100, 125, p.laser_img)]
    s._resolve_player_lasers(p)
    assert s.enemies == [] and p.kills == 1
    assert len(p.lasers) == 1            # second laser was not consumed by a removed target


@pytest.mark.parametrize("health,dies", [(28, True), (27, True), (29, False)])
def test_boss_lethal_boundary(images, health, dies):                                # B13
    s = session(images)
    p = s.players[0]
    boss = Boss(100, 100, images)
    boss.health = health
    s.enemies = [boss]
    p.lasers.append(Laser(110, 150, p.laser_img))
    s._resolve_player_lasers(p)
    assert (boss not in s.enemies) == dies
    assert s.boss_bonus_total == (10 if dies else 0)
    assert boss.health == (0 if dies else 1)


def test_boss_takes_15_hits_and_bonus_once(images):
    s = session(images)
    p = s.players[0]
    boss = Boss(100, 100, images, 400)
    s.enemies = [boss]
    hits = 0
    while boss in s.enemies:
        p.lasers[:] = [Laser(110, 150, p.laser_img), Laser(110, 150, p.laser_img)]  # simultaneous lethal shots
        s._resolve_player_lasers(p)
        hits += 1
    assert hits == 8                     # two per round: 15 hits needed
    assert s.boss_bonus_total == 10 and p.kills == 0
    kinds = [f.kind for f in s.drain_feedback()]
    assert kinds.count("boss_kill") == 1 and kinds.count("hit") == 15


def test_removing_shooter_removes_its_shots(images):
    s = session(images)
    enemy = Enemy(100, 100, "red", images)
    enemy.lasers.append(Laser(410, 470, enemy.laser_img))   # would hit the player next tick
    s.enemies = [enemy]
    p = s.players[0]
    p.lasers.append(Laser(100, 120, p.laser_img))
    s._resolve_player_lasers(p)
    assert s.enemies == []
    s._update_enemies()
    assert p.health == 100


# -- contacts --------------------------------------------------------------------
def _single_enemy_tick(s, enemy):
    s.enemies = [enemy]
    s.pending = []
    s._update_enemies()


def test_contact_with_overlapping_players_damages_first_only(images):            # B3
    s = session(images, "coop")
    enemy = Enemy(410, 480, "red", images)
    _single_enemy_tick(s, enemy)
    assert [p.health for p in s.players] == [85, 100]
    assert s.enemies == [] and s.invasions == 5
    assert sum(p.kills for p in s.players) == 0            # no score for ramming


def test_contact_takes_priority_over_invasion(images):                            # B3
    s = session(images)
    p = s.players[0]
    p.y = HEIGHT - 95
    enemy = Enemy(410, HEIGHT - 50, "red", images)         # also crossing the bottom
    _single_enemy_tick(s, enemy)
    assert p.health == 85 and s.invasions == 5 and s.enemies == []


def test_shield_does_not_block_contact(images):
    s = session(images)
    s.players[0].shield_charges = 3
    _single_enemy_tick(s, Enemy(410, 480, "red", images))
    assert s.players[0].health == 85 and s.players[0].shield_charges == 3


def test_invasion_without_contact(images):
    s = session(images)
    _single_enemy_tick(s, Enemy(10, HEIGHT - 50, "red", images))
    assert s.invasions == 4 and s.enemies == []


def test_boss_contact_is_fatal(images):
    s = session(images)
    boss = Boss(380, 400, images)
    boss.spawn_y = 400
    _single_enemy_tick(s, boss)
    s._check_defeat()
    assert s.defeat_reason == "boss_contact" and s.result.defeat_reason == "boss_contact"
    assert boss in s.enemies


# -- pickups (Task 1.3 / 5.4) -----------------------------------------------------
def _pickup(s, kind, y=480):
    s.packages = [Package(410, y, kind, s.images)]
    s._update_packages()


@pytest.mark.parametrize("kind", ["hp", "triple_laser", "shield"])
def test_pickup_goes_to_one_player(images, kind):                                 # B2
    s = session(images, "coop")
    for p in s.players:
        p.health = 50
    _pickup(s, kind)
    assert s.packages == []
    p1, p2 = s.players
    if kind == "hp":
        assert (p1.health, p2.health) == (100, 50)
    elif kind == "shield":
        assert (p1.shield_charges, p2.shield_charges) == (3, 0)
    else:
        assert (p1.triple_ticks, p2.triple_ticks) == (720, 0)


def test_ineligible_first_player_lets_second_collect(images):
    s = session(images, "coop")
    s.players[1].health = 40
    _pickup(s, "hp")
    assert [p.health for p in s.players] == [100, 100] and s.packages == []


def test_full_health_pack_stays(images):
    s = session(images)
    _pickup(s, "hp")
    assert len(s.packages) == 1


def test_consumed_package_is_not_also_an_exit(images):                            # B4
    s = session(images)
    p = s.players[0]
    p.y = HEIGHT - 95
    p.health = 10
    _pickup(s, "hp", y=HEIGHT - 39)
    assert p.health == 100 and s.packages == []


def test_package_exits_without_pickup(images):
    s = session(images)
    s.packages = [Package(10, HEIGHT - 39, "shield", images)]
    s._update_packages()
    assert s.packages == []


def test_shield_charges_and_fourth_hit(images):
    s = session(images)
    p = s.players[0]
    _pickup(s, "shield")
    enemy = Enemy(0, 0, "red", images)
    for expected_charges, expected_health in [(2, 100), (1, 100), (0, 100), (0, 90)]:
        enemy.lasers[:] = [Laser(420, 470, enemy.laser_img)]
        s._resolve_enemy_lasers(enemy)
        assert (p.shield_charges, p.health) == (expected_charges, expected_health)


def test_shield_refills_only_below_three(images):
    s = session(images)
    s.players[0].shield_charges = 3
    _pickup(s, "shield")
    assert len(s.packages) == 1          # not eligible at full charges
    s.players[0].shield_charges = 1
    _pickup(s, "shield")
    assert s.players[0].shield_charges == 3 and s.packages == []


def test_triple_lasts_720_ticks_and_refreshes_without_stacking(images):
    s = session(images)
    p = s.players[0]
    _pickup(s, "triple_laser")
    s._tick_effects()                    # the pickup tick itself
    for _ in range(718):
        s._tick_effects()
    assert p.triple_active and p.triple_ticks == 1        # 719 ticks elapsed
    _pickup(s, "triple_laser")
    assert p.triple_ticks == 720                           # refresh, never stack
    for _ in range(720):
        s._tick_effects()
    assert not p.triple_active
    assert [f.kind for f in s.drain_feedback()].count("expiry") == 1


def test_effects_carry_across_waves(images):
    s = session(images)
    p = s.players[0]
    p.triple_ticks, p.shield_charges = 500, 2
    s._start_next_wave()
    assert (p.triple_ticks, p.shield_charges) == (500, 2)


def test_package_policy_one_active_replaced_next_update(images):                  # B11 / Task 1.9
    s = GameSession("solo", images, ScriptedRandom(3))
    s.update_step()
    for _ in range(7):
        assert len(s.packages) == 1
        s.packages[0].y = HEIGHT            # exits during this update
        s.update_step()
        assert s.packages == []             # no replacement in the same update
        s.update_step()
        assert len(s.packages) == 1         # replaced on the next update


def test_scores_and_team_total(images):
    s = session(images, "coop")
    s.players[0].kills, s.players[1].kills = 3, 5
    s.boss_bonus_total = 10
    s.players[0].health = 0
    s._check_defeat()
    assert s.result.score == 18 and s.result.kill_points == (3, 5) and s.result.boss_bonus_total == 10
    frozen = s.result
    s.players[1].kills = 99
    s.update_step([PlayerAction(fire=True)])
    assert s.result is frozen and s.result.score == 18


def test_fatal_boss_contact_ends_the_update_before_other_outcomes(images):
    s = GameSession("solo", images, ScriptedRandom(1))
    s.update_step()
    s.pending, s.packages = [], []
    p = s.players[0]
    boss = Boss(p.x - 5, p.y - 100, images)
    boss.spawn_y = p.y - 100 - 100 * __import__("math").sin(0.0525)   # after moving it overlaps the player
    boss.health = 28
    enemy = Enemy(10, 100, "red", images)
    s.enemies = [boss, enemy]
    p.lasers.append(Laser(boss.x + 20, boss.y + 150, p.laser_img))     # lethal shot also overlapping
    s.update_step()
    assert s.defeat_reason == "boss_contact"
    assert s.boss_bonus_total == 0 and boss.health == 28 and s.result.score == 0
    assert enemy.y == 100                                               # later enemies were not advanced


def test_session_balance_reaches_entities(images):
    from space_invaders.settings import Balance
    custom = Balance(player_health=25, player_speed_px_per_tick=1.0, laser_speed_px_per_tick=2.0,
                     triple_side_slope=1.0, boss_health=50)
    s = GameSession("coop", images, ScriptedRandom(1), balance=custom)
    normal = GameSession("coop", images, ScriptedRandom(1))
    assert [p.health for p in s.players] == [25, 25] and [p.health for p in normal.players] == [100, 100]
    x = s.players[0].x
    s.update_step([PlayerAction(dx=1)])
    assert s.players[0].x == x + 1
    s.players[0].triple_ticks = 10
    s.players[0].fire(True)
    side = s.players[0].lasers[0]
    side.move(-2)
    assert side.x == s.players[0].x + 16 - 2
    assert Boss(0, 0, images, balance=custom).health == 50
