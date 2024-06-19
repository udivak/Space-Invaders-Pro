import pygame
import os
import time
import random

pygame.font.init()

WIDTH, HEIGHT = 900, 750
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders Pro")

# Load images
RED_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_red_small.png"))
GREEN_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_green_small.png"))
BLUE_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_blue_small.png"))
# Player Ship
YELLOW_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_yellow.png"))
# Lasers
RED_Laser = pygame.image.load(os.path.join("assets", "pixel_laser_red.png"))
GREEN_Laser = pygame.image.load(os.path.join("assets", "pixel_laser_green.png"))
BLUE_Laser = pygame.image.load(os.path.join("assets", "pixel_laser_blue.png"))
YELLOW_Laser = pygame.image.load(os.path.join("assets", "pixel_laser_yellow.png"))
# Background
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))
# Packages
HP_PACK = pygame.image.load(os.path.join("assets", "healthpack.jpeg"))


class Laser():
    def __init__(self, x, y, img):
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        self.y += vel

    def off_screen(self, height):
        return not (self.y <= height and self.y >= 0)

    def collision(self, obj):
        return collide(self, obj)


class Ship:
    COOLDOWN = 17

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

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1

        if self.cooldown_meter < 100:
            self.cooldown_meter += 0.7


class Package:
    package_type = {
        'hp': HP_PACK
    }

    def __init__(self, x, y, img):
        self.x = x
        self.y = y
        self.img = self.package_type[img]
        self.mask = pygame.mask.from_surface(self.img)

    def collision(self, obj):
        return collide(self, obj)

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        self.y += vel


class Player(Ship):
    def __init__(self, x, y, health=100):
        super().__init__(x, y, health)
        self.ship_img = YELLOW_SPACE_SHIP
        self.laser_img = YELLOW_Laser
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health
        self.score = 0
        self.cooldown_meter = 0

    def move_lasers(self, vel, objs):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs:
                    if laser.collision(obj):
                        self.score += 1
                        objs.remove(obj)
                        if laser in self.lasers:
                            self.lasers.remove(laser)

    def healthbar(self, window):
        pygame.draw.rect(window, (255, 0, 0),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (0, 255, 0),
                         (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() *
                          (self.health / self.max_health), 10))

    def shooting_meter(self, window):
        pygame.draw.rect(window, (255, 125, 0), (self.x, self.y + self.ship_img.get_height() + 20,
                                                 self.cooldown_meter, 7))

    def draw(self, window):
        super().draw(window)
        self.healthbar(window)
        self.shooting_meter(window)


class Enemy(Ship):
    COLOR_MAP = {'red': (RED_SPACE_SHIP, RED_Laser),
                 'green': (GREEN_SPACE_SHIP, GREEN_Laser),
                 'blue': (BLUE_SPACE_SHIP, BLUE_Laser)}

    def __init__(self, x, y, color, health=100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)

    def move(self, vel):  # enemy moves downwards
        self.y += vel

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x - 17, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1


def collide(obj1, obj2):
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None


def main():
    run = True
    FPS = 60
    level = 0
    lives = 5
    main_font = pygame.font.SysFont("comicsans", 30)
    lost_font = pygame.font.SysFont("comicsans", 60)
    player_vel = 7
    player = Player(380, 600)
    lost = False
    lost_count = 0
    enemies = []
    wave_length = 10
    enemy_vel = 1
    laser_vel = 6.5
    packages = []

    clock = pygame.time.Clock()

    def redraw_window():
        WIN.blit(BG, (0, 0))
        # draw text
        lives_label = main_font.render(f"Lives : {lives}", 1, (255, 0, 0))
        level_label = main_font.render(f"Level : {level}", 1, (255, 255, 255))
        level_label = main_font.render(f"Level : {level}", 1, (255, 255, 255))
        score_label = main_font.render(f"Score : {player.score}", 1, (0, 255, 0))
        WIN.blit(score_label, (WIDTH / 2 - score_label.get_width() / 2 - 10, 15))
        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        for pack in packages:
            pack.draw(WIN)

        player.draw(WIN)

        if lost:
            lost_label = lost_font.render("Game Over !!!", 1, (0, 50, 255))
            WIN.blit(lost_label, (WIDTH / 2 - lost_label.get_width() / 2, 350))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        redraw_window()

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 2
            if level > 1:
                if player.health < 100 and player.health >= 80:
                    player.health = 100
                if player.health < 70:
                    player.health += 20
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH - 100), random.randrange(-1500, -100),
                              random.choice(['red', 'blue', 'green']))
                enemies.append(enemy)

        if len(packages) == 0:
            package = Package(random.randrange(50, WIDTH - 100), random.randrange(-1500, -100),
                              random.choice(['hp']))
            packages.append(package)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT] and player.x + player_vel + player.get_width < WIDTH:  # right
            player.x += player_vel
        if keys[pygame.K_UP] and player.y - player_vel > 0:  # up
            player.y -= player_vel
        if keys[pygame.K_DOWN] and player.y + player_vel + player.get_height + 20 < HEIGHT:  # down
            player.y += player_vel
        if keys[pygame.K_LEFT] and player.x - player_vel > 0:  # left
            player.x -= player_vel
        if keys[pygame.K_SPACE]:
            if player.cooldown_meter < 100:
                player.shoot()
        if not keys[pygame.K_SPACE]:
            if player.cooldown_meter >= 0:
                player.cooldown_meter -= 0.7

        for pack in packages:
            pack.move(1)
            if collide(pack, player):
                player.health = 100
                packages.remove(pack)

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player)
            if random.randrange(0, 2 * 60) == 1:
                enemy.shoot()
            if collide(enemy, player):
                player.health -= 10
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        player.move_lasers(-laser_vel, enemies)


def main_menu():
    title_font = pygame.font.SysFont("comicsans", 30)
    run = True
    while run:
        WIN.blit(BG, (0, 0))
        title_label1 = title_font.render("Welcome to Space Invaders Pro !!!", 1, (255, 255, 255))
        title_label2 = title_font.render("Press the mouse to begin...", 1, (255, 255, 255))
        title_label3 = title_font.render("~ Use arrows to move, Spacebar to shoot ~", 1, (255, 255, 255))
        WIN.blit(title_label3, (WIDTH / 2 - title_label3.get_width() / 2, 400))
        WIN.blit(title_label1, (WIDTH / 2 - title_label1.get_width() / 2, 300))
        WIN.blit(title_label2, (WIDTH / 2 - title_label1.get_width() / 2 + 30, 500))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                main()
    pygame.quit()


main_menu()
