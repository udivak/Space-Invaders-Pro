# Ships Classes - Ship, Player, Enemy
import pygame
import os
import time
import random
import pygame.math

# Assets :
#WIDTH, HEIGHT = 900, 750
WIDTH, HEIGHT = 1000, 850
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders Pro")

# Load images
# Enemies
RED_SPACE_SHIP = pygame.image.load(os.path.join("assets", "enemy - red.png"))
GREEN_SPACE_SHIP = pygame.image.load(os.path.join("assets", "enemy - green.png"))
BLUE_SPACE_SHIP = pygame.image.load(os.path.join("assets", "enemy - blue.png"))
# Player Ship
PLAYER_SHIP = pygame.image.load(os.path.join("assets", "player.png"))
# Boss Ship
BOSS_GREY = pygame.image.load(os.path.join("assets", "boss_grey.png"))
# Lasers
PLAYER_LASER = pygame.image.load(os.path.join("assets", "player_laser.png"))
BOSS_PURPLE_LASER = pygame.image.load(os.path.join("assets", "boss_laser_purple.png"))
ENEMY_BLUE_LASER = pygame.image.load(os.path.join("assets", "enemy_laser_blue.png"))
ENEMY_RED_LASER = pygame.image.load(os.path.join("assets", "enemy_laser_red.png"))
ENEMY_GREEN_LASER = pygame.image.load(os.path.join("assets", "enemy_laser_green.png"))
# Background
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))
# Packages
HP_PACK = pygame.image.load(os.path.join("assets", "healthpack.jpeg"))
TRIPLE_LASER = pygame.image.load(os.path.join("assets", "laserpack.png"))
# # #

# Laser :
class Laser():
    def __init__(self, x, y, img,triple_flag = False, angle_right_flag = False):
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)
        self.triple_flag = triple_flag
        self.angle_right_flag = angle_right_flag
    def draw(self, window):
        window.blit(self.img, (self.x, self.y))
    def move(self, vel):
        if self.triple_flag:
            if self.angle_right_flag:
                self.x -= 0.4 * vel
            else:
                self.x += 0.4 * vel
        self.y += vel
    def off_screen(self, height):
        return not (self.y <= height and self.y >= 0)
    def collision(self, obj):
        return collide(self, obj)
# # # Class Laser # # #

# Ships :
class Ship:
    COOLDOWN = 17   # between lasers
    def __init__(self, x, y, health=100):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers = []
        self.cool_down_counter = 0
    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)
    def move_lasers(self, vel, obj):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                obj.health -= 10
                self.lasers.remove(laser)
    def cooldown(self):
        if self.cool_down_counter >= self.COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1
    @property
    def get_width(self):
        return self.ship_img.get_width()
    @property
    def get_height(self):
        return self.ship_img.get_height()

# Player
class Player(Ship):
    def __init__(self, x, y, health=100):
        super().__init__(x, y, health)
        self.ship_img = PLAYER_SHIP
        self.laser_img = PLAYER_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health
        self.score = 0
        self.cooldown_meter = 0
        self.pack_flag = {'hp': False, 'triple_shot': False}
        self.triple_shot_counter = 0
    def shoot(self):
        '''if self.cool_down_counter == 0:
            laser = Laser(self.x+16, self.y-45, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1'''
        if self.cooldown_meter < self.ship_img.get_width():
            self.cooldown_meter += 0.35
            if self.cool_down_counter == 0:
                laser = Laser(self.x + 16, self.y - 45, self.laser_img)
                self.lasers.append(laser)
                self.cool_down_counter = 1
    def triple_shot(self):
        if self.cooldown_meter < self.ship_img.get_width():
            self.cooldown_meter += 0.35
        if self.cool_down_counter == 0:
            laser1 = Laser(self.x + 16, self.y - 45, self.laser_img, True)
            laser2 = Laser(self.x + 16, self.y - 45, self.laser_img)            # Default direcion
            laser3 = Laser(self.x + 16, self.y - 45, self.laser_img, True, True)
            self.lasers.extend([laser1, laser2, laser3])
            self.cool_down_counter = 1
    def move_lasers(self, vel, enemies):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in enemies:
                    if laser.collision(obj):
                        if isinstance(obj, Boss):
                            if obj.health >= 23:
                                obj.health -= 23
                            else:
                                enemies.remove(obj)
                        else:
                            self.score += 1
                            enemies.remove(obj)
                        if laser in self.lasers:
                            self.lasers.remove(laser)
    def healthbar(self, window):
        pygame.draw.rect(window, (255, 0, 0),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (0, 255, 170),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() *
                          (self.health / self.max_health), 10))
    def shooting_meter(self, window):
        pygame.draw.rect(window, (255, 125, 0), (self.x, self.y + self.ship_img.get_height() + 20,
                                                            self.cooldown_meter, 7))
    def draw(self, window):
        super().draw(window)
        self.healthbar(window)
        self.shooting_meter(window)

# Enemy
class Enemy(Ship):
    COLOR_MAP = {'red': (RED_SPACE_SHIP, ENEMY_RED_LASER),
                 'green': (GREEN_SPACE_SHIP, ENEMY_GREEN_LASER),
                 'blue': (BLUE_SPACE_SHIP, ENEMY_BLUE_LASER)}
    def __init__(self, x, y, color, health=100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img  = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)
    def move(self, vel):  # enemy moves downwards
        self.y += vel
    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1

# Boss
class Boss(Ship):
    COLOR_MAP = {'grey': (BOSS_GREY, BOSS_PURPLE_LASER)}
    def __init__(self, x, y, color, health = 300):
        super().__init__(x, y, health)
        self.spawn_point = (x, y)
        self.ship_img, self.laser_img = self.COLOR_MAP[color] # -> color
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health
    def move(self, vel):    #fix boss moving mechanism
        '''if self.y + self.ship_img.get_height() > HEIGHT:
            self.y = 400
        if self.x + self.ship_img.get_width() > WIDTH:
            self.x = 400
        self.x += random.choice([-1, 1, 1, 1, 1, 1, 1]) * vel
        self.y += random.choice([-1, 1, 1, 1, 1, 1, 1]) * vel'''

        '''large_movement_chance = 0.8
        x_move = random.randint(-10, 10)
        y_move = random.randint(-10, 10)
        self.x += x_move
        self.y += y_move
        if random.random() < large_movement_chance:
            # Increase the chance of larger movements by a factor
            x_move = int(x_move * 9)  # You can adjust the factor here
            y_move = int(y_move * 9)
        # Ensure the boss stays within the window boundaries
        self.x = min(max(self.x, 0), WIDTH - self.ship_img.get_width())
        self.y = min(max(self.y, 0), WIDTH - self.ship_img.get_height())'''
        movement_tendency = 0.9
        distance_from_spawn = ((self.x - self.spawn_point[0]) ** 2 + (self.y - self.spawn_point[1]) ** 2) ** 0.5
        movement_direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        movement_scale = 1 - min(distance_from_spawn / WIDTH, movement_tendency)
        movement = movement_direction.normalize() * vel
        self.x += movement.x
        self.y += movement.y
        # Ensure the boss stays within the window boundaries
        self.x = min(max(self.x, 0), WIDTH - self.ship_img.get_width())
        self.y = min(max(self.y, 0), WIDTH - self.ship_img.get_height())
    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1
    def healthbar(self, window):
        pygame.draw.rect(window, (255, 0, 0),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (150, 0, 210),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() *
                          (self.health / self.max_health), 10))
    def draw(self, window):
        super().draw(window)
        self.healthbar(window)
# # # Ships Classes # # #

# Package :
class Package:
    package_type = {
        'hp': HP_PACK, 'triple_laser' : TRIPLE_LASER
    }
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.img = self.package_type[type]
        self.mask = pygame.mask.from_surface(self.img)
        self.type = type
    def collision(self, obj):
        return collide(self, obj)
    def draw(self, window):
        window.blit(self.img, (self.x, self.y))
    def move(self, vel):
        self.y += vel
# # # Class Package # # #


def collide(obj1, obj2):
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None
