"""Entities: position, health, sprite/mask, movement and simple drawing.

Collision outcomes, damage and scoring are resolved by GameSession.
"""
import math

import pygame

from space_invaders.settings import (BALANCE, HEIGHT, WIDTH, HEALTH_BACK, HEALTH_FRONT, HEAT_COLOR,
                                     SHIELD_RING)


def collide(obj1, obj2):
    offset = (int(obj2.x - obj1.x), int(obj2.y - obj1.y))
    return obj1.mask.overlap(obj2.mask, offset) is not None


class Laser:
    def __init__(self, x, y, img, triple_flag=False, angle_right_flag=False, balance=BALANCE):
        self.balance = balance
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(img)
        self.triple_flag = triple_flag
        self.angle_right_flag = angle_right_flag

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        if self.triple_flag:
            if self.angle_right_flag:
                self.x -= self.balance.triple_side_slope * vel
            else:
                self.x += self.balance.triple_side_slope * vel
        self.y += vel

    def off_screen(self, height=HEIGHT):
        return not (0 <= self.y <= height)

    def collision(self, obj):
        return collide(self, obj)


class Ship:
    def __init__(self, x, y, ship_img, laser_img, health=100, balance=BALANCE):
        self.balance = balance
        self.x = x
        self.y = y
        self.health = health
        self.max_health = health
        self.ship_img = ship_img
        self.laser_img = laser_img
        self.mask = pygame.mask.from_surface(ship_img)
        self.lasers = []
        self.cool_down_counter = 0

    @property
    def width(self):
        return self.ship_img.get_width()

    @property
    def height(self):
        return self.ship_img.get_height()

    def cooldown(self):
        if self.cool_down_counter >= self.balance.shot_cooldown_ticks:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1

    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)


class Player(Ship):
    def __init__(self, x, y, images, player_id=1, balance=BALANCE):
        suffix = "2" if player_id == 2 else ""
        super().__init__(x, y, images["player" + suffix], images[f"player{suffix}_laser"], balance.player_health,
                         balance)
        self.player_id = player_id
        self.kills = 0
        self.heat = 0.0
        self.triple_ticks = 0
        self.shield_charges = 0

    @property
    def triple_active(self):
        return self.triple_ticks > 0

    @property
    def shield_active(self):
        return self.shield_charges > 0

    @property
    def overheated(self):
        return self.heat >= self.balance.heat_capacity

    def move(self, dx, dy):
        v = self.balance.player_speed_px_per_tick
        if dx > 0 and self.x + v + self.width < WIDTH:
            self.x += v
        if dy < 0 and self.y - v > 0:
            self.y -= v
        if dy > 0 and self.y + v + self.height + 20 < HEIGHT:
            self.y += v
        if dx < 0 and self.x - v > 0:
            self.x -= v

    def fire(self, held):
        """Apply one tick of the fire control. Returns True when lasers were created."""
        if not held:
            self.heat = max(0.0, self.heat - self.balance.heat_cooling_per_tick)
            return False
        if self.overheated:
            return False
        per_tick = self.balance.heat_per_triple_tick if self.triple_active else self.balance.heat_per_shot_tick
        self.heat = min(self.balance.heat_capacity, self.heat + per_tick)
        if self.cool_down_counter != 0:
            return False
        x, y = self.x + 16, self.y - 45
        if self.triple_active:
            self.lasers.extend([Laser(x, y, self.laser_img, True, False, self.balance),
                                Laser(x, y, self.laser_img, balance=self.balance),
                                Laser(x, y, self.laser_img, True, True, self.balance)])
        else:
            self.lasers.append(Laser(x, y, self.laser_img, balance=self.balance))
        self.cool_down_counter = 1
        return True

    def draw(self, window):
        if self.shield_active:
            center = (self.x + self.width // 2, self.y + self.height // 2)
            pygame.draw.circle(window, SHIELD_RING, center, 60, 2)
        super().draw(window)
        bar_y = self.y + self.height + 10
        pygame.draw.rect(window, HEALTH_BACK, (self.x, bar_y, self.width, 10))
        pygame.draw.rect(window, HEALTH_FRONT,
                         (self.x, bar_y, self.width * max(0, self.health) / self.max_health, 10))
        pygame.draw.rect(window, HEAT_COLOR, (self.x, bar_y + 10, self.heat, 7))


class Enemy(Ship):
    COLORS = ("red", "blue", "green")

    def __init__(self, x, y, color, images, health=100, balance=BALANCE):
        super().__init__(x, y, images["enemy_" + color], images["enemy_laser_" + color], health, balance)
        self.color = color
        self.lane_x = x
        self.weave_phase = 0.0
        if color == "blue":
            amplitude = self.balance.weave_amplitude_px
            self.lane_x = min(max(x, amplitude), WIDTH - self.width - amplitude)
            self.x = self.lane_x

    def move(self, vel=None):
        self.y += self.balance.enemy_speed_px_per_tick if vel is None else vel
        if self.color == "blue":
            self.weave_phase += self.balance.weave_phase_per_tick
            self.x = self.lane_x + self.balance.weave_amplitude_px * math.sin(self.weave_phase)

    def shoot(self):
        if self.cool_down_counter == 0:
            self.lasers.append(Laser(self.x, self.y, self.laser_img, balance=self.balance))
            self.cool_down_counter = 1
            return True
        return False


class Boss(Ship):
    def __init__(self, x, y, images, health=None, balance=BALANCE):
        health = balance.boss_health if health is None else health
        super().__init__(x, y, images["boss_grey"], images["boss_laser"], health, balance)
        self.spawn_y = y
        self.phase = 0.0
        self.attack_timer = 0
        self.attack_phase = 1
        self.telegraph_ticks = 0

    def move(self):
        self.x += self.balance.boss_speed_px_per_tick
        self.phase += self.balance.boss_phase_per_tick
        self.y = self.spawn_y + self.balance.boss_amplitude_px * math.sin(self.phase)
        if self.x > WIDTH:
            self.x = 0

    def visible(self):
        return self.x < WIDTH and self.x + self.width > 0 and self.y < HEIGHT and self.y + self.height > 0

    def update_attack(self):
        """Advance the boss attack timer one tick. Returns the number of shots fired."""
        if self.attack_phase == 1 and self.health <= self.max_health / 2:
            self.attack_phase = 2
            self.telegraph_ticks = self.balance.boss_telegraph_ticks
            self.attack_timer = 0
        if self.telegraph_ticks > 0:
            self.telegraph_ticks -= 1
            if self.telegraph_ticks > 0:
                return 0
            # Telegraph finished: the announced volley fires now.
            self.attack_timer = self.balance.boss_phase2_interval_ticks
        else:
            self.attack_timer += 1
        interval = (self.balance.boss_phase1_interval_ticks if self.attack_phase == 1
                    else self.balance.boss_phase2_interval_ticks)
        if self.attack_timer < interval:
            return 0
        self.attack_timer = 0
        if not self.visible():
            return 0
        x, y = self.x + self.width / 4, self.y + self.height / 2 + 40
        if self.attack_phase == 1:
            self.lasers.append(Laser(x, y, self.laser_img, balance=self.balance))
            return 1
        self.lasers.extend([Laser(x, y, self.laser_img, True, False, self.balance),
                            Laser(x, y, self.laser_img, balance=self.balance),
                            Laser(x, y, self.laser_img, True, True, self.balance)])
        return 3

    @property
    def telegraphing(self):
        return self.telegraph_ticks > 0


class Package:
    TYPES = ("hp", "triple_laser", "shield")

    def __init__(self, x, y, kind, images, balance=BALANCE):
        self.balance = balance
        self.x = x
        self.y = y
        self.kind = kind
        self.img = images["pack_" + kind]
        self.mask = pygame.mask.from_surface(self.img)

    @property
    def height(self):
        return self.img.get_height()

    def collision(self, obj):
        return collide(self, obj)

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel=None):
        self.y += self.balance.package_speed_px_per_tick if vel is None else vel
