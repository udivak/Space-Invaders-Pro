import pygame
import os
import time
import random

from Classes import *

pygame.font.init()


def main():
    run = True
    FPS = 60
    level = 0
    invades = 5
    main_font = pygame.font.SysFont("comicsans", 30)
    lost_font = pygame.font.SysFont("comicsans", 60)
    player_vel = 7.2
    player = Player(WIDTH/2 - PLAYER_SHIP.get_width()/2 - 20, HEIGHT - PLAYER_SHIP.get_height() - 80)
    lost = False
    lost_count = 0
    enemies = []
    wave_length = 10
    enemy_vel = 1
    laser_vel = 8.5
    packages = []
    boss = None
    boss_flag = False
    clock = pygame.time.Clock()

    def redraw_window():
        WIN.blit(BG, (0, 0))
        # draw text
        lives_label = main_font.render(f"Invades : {invades}", 1, (255, 0, 0))
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

        if invades <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
            else:
                continue

        if len(enemies) == 0: # finished level
            level += 1
            if level > 1 and invades < 5:
                invades += 1
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
            if level % 2 == 1:
                boss = Boss(random.randrange(50, WIDTH - 100), random.randrange(-1500, -100),
                            random.choice(['grey']))
                enemies.append(boss)

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
                player.cooldown_meter -= 0.60

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
            if collide(enemy, player) and isinstance(enemy, Enemy):
                player.health -= 10
                enemies.remove(enemy)
            if isinstance(enemy, Enemy) and enemy.y + enemy.get_height > HEIGHT:
                invades -= 1
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
