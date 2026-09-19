"""GameSession owns the simulation: entities, combat outcomes, scoring, waves and defeat.

update_step advances exactly one 60-Hz tick and performs no event, clock, display, sound or file work.
"""
import random
import uuid
from dataclasses import dataclass

from space_invaders import waves
from space_invaders.entities import Boss, Enemy, Package, Player, collide
from space_invaders.settings import BALANCE, HEIGHT, RULESET, WIDTH


@dataclass(frozen=True)
class PlayerAction:
    dx: int = 0
    dy: int = 0
    fire: bool = False


IDLE = PlayerAction()


@dataclass(frozen=True)
class Feedback:
    kind: str          # shot, hit, player_hit, shield_block, kill, boss_kill, pickup, expiry
    x: float = 0
    y: float = 0
    target: object = None


@dataclass(frozen=True)
class RunResult:
    run_id: str
    mode: str
    ruleset: str
    level: int
    kill_points: tuple
    boss_bonus_total: int
    defeat_reason: str      # health, breaches or boss_contact

    @property
    def score(self):
        return sum(self.kill_points) + self.boss_bonus_total


class GameSession:
    def __init__(self, mode, images, rng=None, balance=BALANCE, ruleset=RULESET):
        if mode not in ("solo", "coop"):
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        self.images = images
        self.rng = rng if rng is not None else random.Random()
        self.balance = balance
        self.ruleset = ruleset
        self.run_id = uuid.uuid4().hex
        height = images["player"].get_height()
        if mode == "coop":
            self.players = [Player(600, HEIGHT - height - 80, images, 1, balance),
                            Player(200, HEIGHT - height - 80, images, 2, balance)]
        else:
            width = images["player"].get_width()
            self.players = [Player(WIDTH / 2 - width / 2 - 20, HEIGHT - height - 80, images, 1, balance)]
        self.enemies = []
        self.packages = []
        self.pending = []
        self.level = 0
        self.invasions = balance.max_invasions
        self.boss_bonus_total = 0
        self.wave_tick = 0
        self.defeat_reason = None
        self.result = None
        self.feedback = []
        self.ticks = 0

    # -- public -----------------------------------------------------------------
    @property
    def defeated(self):
        return self.defeat_reason is not None

    @property
    def score(self):
        return sum(p.kills for p in self.players) + self.boss_bonus_total

    @property
    def boss(self):
        return next((e for e in self.enemies if isinstance(e, Boss)), None)

    @property
    def boss_incoming(self):
        return any(spec.kind == "boss" for spec in self.pending)

    def drain_feedback(self):
        feedback, self.feedback = self.feedback, []
        return feedback

    def update_step(self, actions=()):
        """Advance one simulation tick. actions: one PlayerAction per player."""
        if self.defeated:
            return
        self.ticks += 1
        if not self.enemies and not self.pending:
            self._start_next_wave()
        self._spawn_due()
        if not self.packages:
            x, y, kind = waves.package_spec(self.rng)
            self.packages.append(Package(x, y, kind, self.images, self.balance))
        actions = list(actions) + [IDLE] * (len(self.players) - len(actions))
        for player, action in zip(self.players, actions):
            player.move(action.dx, action.dy)
            if player.fire(action.fire):
                self._emit("shot", player)
        self._update_packages()
        self._update_enemies()
        if self.defeated:                     # fatal boss contact ends the run before further outcomes
            self._check_defeat()
            return
        for player in self.players:
            self._resolve_player_lasers(player)
        self._tick_effects()
        self._check_defeat()

    # -- waves ------------------------------------------------------------------
    def _start_next_wave(self):
        self.level += 1
        if self.level > 1:
            if self.invasions < self.balance.max_invasions:
                self.invasions += 1
            for player in self.players:
                player.health = min(player.max_health, player.health + self.balance.wave_heal)
        enemy_height = self.images["enemy_red"].get_height()
        self.pending = waves.build_wave(self.level, self.mode, self.rng, enemy_height, self.balance)
        self.wave_tick = 0

    def _spawn_due(self):
        while self.pending and self.pending[0].tick <= self.wave_tick:
            spec = self.pending.pop(0)
            if spec.kind == "boss":
                self.enemies.append(Boss(spec.x, spec.y, self.images, balance=self.balance))
            else:
                self.enemies.append(Enemy(spec.x, spec.y, spec.color, self.images, balance=self.balance))
        self.wave_tick += 1

    # -- packages ---------------------------------------------------------------
    def _eligible(self, player, package):
        if package.kind == "hp":
            return player.health < player.max_health
        if package.kind == "shield":
            return player.shield_charges < self.balance.shield_charges
        return True

    def _apply_package(self, player, package):
        if package.kind == "hp":
            player.health = player.max_health
        elif package.kind == "shield":
            player.shield_charges = self.balance.shield_charges
        else:
            player.triple_ticks = self.balance.triple_duration_ticks

    def _update_packages(self):
        for package in self.packages[:]:
            package.move(self.balance.package_speed_px_per_tick)
            recipient = next((p for p in self.players if collide(package, p) and self._eligible(p, package)), None)
            if recipient is not None:
                self._apply_package(recipient, package)
                self.packages.remove(package)
                self._emit("pickup", recipient, package.kind)
            elif package.y + package.height > HEIGHT:
                self.packages.remove(package)

    # -- enemies ----------------------------------------------------------------
    def _update_enemies(self):
        for enemy in self.enemies[:]:
            if enemy not in self.enemies:
                continue
            if isinstance(enemy, Boss):
                enemy.move()
                enemy.update_attack()
            else:
                enemy.move(self.balance.enemy_speed_px_per_tick)
                if self.rng.randrange(0, self.balance.enemy_shot_chance) == 1:
                    enemy.shoot()
            self._resolve_enemy_lasers(enemy)
            contact = next((p for p in self.players if collide(enemy, p)), None)
            if contact is not None:
                if isinstance(enemy, Boss):
                    self.defeat_reason = "boss_contact"
                    return
                contact.health -= self.balance.contact_damage
                self.enemies.remove(enemy)
                self._emit("player_hit", contact)
                continue
            if not isinstance(enemy, Boss) and enemy.y + enemy.height > HEIGHT:
                self.invasions -= 1
                self.enemies.remove(enemy)

    def _resolve_enemy_lasers(self, shooter):
        shooter.cooldown()
        for laser in shooter.lasers[:]:
            laser.move(self.balance.laser_speed_px_per_tick)
            if laser.off_screen(HEIGHT):
                shooter.lasers.remove(laser)
                continue
            target = next((p for p in self.players if laser.collision(p)), None)
            if target is None:
                continue
            if target.shield_charges > 0:
                target.shield_charges -= 1
                self._emit("shield_block", target)
            else:
                target.health -= self.balance.bullet_damage
                self._emit("player_hit", target)
            shooter.lasers.remove(laser)

    def _resolve_player_lasers(self, player):
        player.cooldown()
        for laser in player.lasers[:]:
            laser.move(-self.balance.laser_speed_px_per_tick)
            if laser.off_screen(HEIGHT):
                player.lasers.remove(laser)
                continue
            target = next((e for e in self.enemies if laser.collision(e)), None)
            if target is None:
                continue
            player.lasers.remove(laser)
            if isinstance(target, Boss):
                target.health = max(0, target.health - self.balance.boss_hit_damage)
                self._emit("hit", target)
                if target.health <= 0:
                    self.enemies.remove(target)
                    self.boss_bonus_total += self.balance.boss_bonus
                    self._emit("boss_kill", target)
            else:
                player.kills += self.balance.kill_points
                self.enemies.remove(target)
                self._emit("kill", target)

    # -- effects and defeat -----------------------------------------------------
    def _tick_effects(self):
        for player in self.players:
            if player.triple_ticks > 0:
                player.triple_ticks -= 1
                if player.triple_ticks == 0:
                    self._emit("expiry", player, "triple_laser")

    def _check_defeat(self):
        if self.defeat_reason is None:
            if any(p.health <= 0 for p in self.players):
                self.defeat_reason = "health"
            elif self.invasions <= 0:
                self.defeat_reason = "breaches"
        if self.defeat_reason is not None and self.result is None:
            self.result = RunResult(self.run_id, self.mode, self.ruleset, self.level,
                                    tuple(p.kills for p in self.players), self.boss_bonus_total,
                                    self.defeat_reason)

    def _emit(self, kind, obj, target=None):
        self.feedback.append(Feedback(kind, obj.x + obj.width / 2 if hasattr(obj, "width") else obj.x,
                                      obj.y, target if target is not None else obj))

    # -- drawing ----------------------------------------------------------------
    def draw(self, surface):
        for enemy in self.enemies:
            enemy.draw(surface)
        for package in self.packages:
            package.draw(surface)
        for player in self.players:
            player.draw(surface)
