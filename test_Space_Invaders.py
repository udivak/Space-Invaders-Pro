import unittest
import Classes
import main
import pytest
import pygame
from main import *
from Classes import *
# Classes Methods Tests
def test_laser_movement():
    laser = Laser(0, 0, PLAYER_LASER)
    laser.move(10)
    assert laser.y == 10
    for _ in range(10):
        laser.move(1)
    assert laser.y == 20
def test_laser_off_screen():
    laser = Laser(0, 50, PLAYER_LASER)
    height = 100
    assert laser.off_screen(height) == False
    laser.move(70)
    assert laser.off_screen(height) == True
def test_collision():
    laser = Laser(0, 0, PLAYER_LASER)
    player = Player(0, 0)
    assert laser.collision(player) == True
    laser.move(100)
    assert laser.collision(player) == False
def test_get_height():
    player = Player(0, 0)
    height = PLAYER_SHIP.get_height()
    assert player.get_height == height
def test_get_width():
    player = Player(0, 0)
    width = PLAYER_SHIP.get_width()
    assert player.get_width == width
def test_player_shoot():
    player = Player(0, 0)
    player.shoot()
    assert len(player.lasers) == 1
def test_player_triple_shot():
    player = Player(0, 0)
    player.triple_shot()
    assert len(player.lasers) == 3
def test_enemy_move():
    enemy = Enemy(0, 0, random.choice(['red', 'green', 'blue']))
    enemy.move(10)
    assert enemy.y == 10
def test_enemy_shoot():
    enemy = Enemy(0, 0, random.choice(['red', 'green', 'blue']))
    enemy.shoot()
    assert len(enemy.lasers) == 1
def test_boss_move():
    amplitude = 100  # Height of the wave
    frequency = 0.03  # Speed of the wave
    boss = Boss(0, 0, 'grey')
    boss.move()
    assert boss.x == 1.75
    assert boss.y == amplitude * math.sin(boss.x * frequency)
def test_boss_shoot():
    boss = Boss(0, 0, 'grey')
    boss.shoot()
    assert len(boss.lasers) == 1
def test_package_collision():
    package = Package(0, 0, random.choice(['hp', 'triple_laser', 'shield']))
    player = Player(0, 0)
    assert package.collision(player) == True
    package.move(500)
    assert package.collision(player) == False
def test_package_get_height():
    pack_type = random.choice(['hp', 'triple_laser', 'shield'])
    package = Package(0, 0, pack_type)
    assert package.get_height == Package.package_type[pack_type].get_height()
# # #

# Main Tests
def test_save_score():
    score = 100
    name = 'test'
    save_score(name, score)
    target = f"({name}, {score})"
    with open('scores.txt', 'r') as file:
        content = file.read()
    assert target in content


