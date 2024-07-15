import random
import time
import pygame
from Classes import *
pygame.init()
pygame.font.init()
pygame.mixer.music.set_volume(0.055)
player2_flag = False
def main():
    run = True
    FPS = 60
    level = 0
    invades = 5
    main_font = pygame.font.SysFont("comicsans", 30)
    lost_font = pygame.font.SysFont("comicsans", 60)
    player_vel = 7.4
    max_health = 100
    if player2_flag:
        player = Player(600, HEIGHT - PLAYER_SHIP.get_height() - 80, max_health)
        player2 = Player(200, HEIGHT - PLAYER_SHIP.get_height() - 80, max_health, 2)
        players = [player, player2]
    else:
        player = Player(WIDTH / 2 - PLAYER_SHIP.get_width() / 2 - 20, HEIGHT - PLAYER_SHIP.get_height() - 80,max_health)
        player2 = None
        players = [player]
    lost = False
    lost_count = 0
    enemies = []
    wave_length = 10
    enemy_vel, package_vel = 1, 1.4
    laser_vel = 10.5
    packages = []
    boss = None
    clock = pygame.time.Clock()
    def redraw_window():
        #nonlocal player, player2
        WIN.blit(BG, (0, 0))
        # draw variables
        lives_label = main_font.render(f"Invades : {invades}", 1, (255, 0, 0))
        level_label = main_font.render(f"Level : {level}", 1, (255, 255, 255))
        if player2_flag:
            score_label1 = main_font.render(f"Score : {players[0].score}", 1, (65, 105, 255))
            score_label2 = main_font.render(f"Score : {players[1].score}", 1, (255, 140, 0))
            WIN.blit(score_label1, (600 - 10, 10))
            WIN.blit(score_label2, (220, 10))
        else:
            score_label = main_font.render(f"Score : {players[0].score}", 1, (65, 105, 255))
            WIN.blit(score_label, (WIDTH / 2 - score_label.get_width() / 2 - 10, 10))
        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))
        for enemy in enemies:
            enemy.draw(WIN)
        for pack in packages:
            pack.draw(WIN)
        for player in players:
            player.draw(WIN)
        if lost:
            lost_label = lost_font.render("Game Over !!!", 1, (0, 170, 255))
            WIN.blit(lost_label, (WIDTH / 2 - lost_label.get_width() / 2, HEIGHT/2 - lost_label.get_height()/2))
            pygame.display.update()
            time.sleep(1.5)
            if player2_flag:
                game_over(max(players[0].score, players[1].score))
            else:
                game_over(player.score)
        pygame.display.update()

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                return  # Exit the function entirely

        clock.tick(FPS)
        redraw_window()
        if player2_flag:
            if invades <= 0 or players[0].health <= 0 or players[1].health <= 0 or lost:
                lost = True
                lost_count += 1
        else:
            if invades <= 0 or players[0].health <= 0 or lost:
                lost = True
                lost_count += 1
        if len(enemies) == 0:   # finished level
            level += 1
            wave_length += 2
            if level > 1:
                invades += 1
            if level > 1:
                for player in players:
                    if player.health < 100 and player.health >= 80:
                        player.health = 100
                    if player.health < 80:
                        player.health += 20
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH - 100), random.randrange(-1500, -100),
                              random.choice(['red', 'blue', 'green']))
                enemies.append(enemy)
            if level > 2 and level % 2 == 1:
                boss = Boss(random.randrange(int(WIDTH * 0.25), int(WIDTH * 0.75)), random.randrange(100, 300),
                            random.choice(['grey']), 400)
                enemies.append(boss)
            for player in players:
                if player.pack_flag['triple_shot']:
                    player.pack_flag['triple_shot'] = False
                if player.pack_flag['shield']:
                    player.pack_flag['shield'] = False
            '''if player.pack_flag['triple_shot']:              # keep the package for 2 levels
                player.pack_duration['triple_shot'] += 1
                if player.pack_duration['triple_shot'] > 1:
                    player.pack_duration['triple_shot'] = 0
                    player.pack_flag['triple_shot'] = False
            if player.pack_flag['shield']:
                player.pack_duration['shield'] += 1
                if player.pack_duration['shield'] > 1:
                    player.pack_duration['shield'] = 0
                    player.pack_flag['shield'] = False'''
        package_counter = 0
        if len(packages) == 0 and package_counter <= 2:
            package = Package(random.randrange(50, WIDTH - 100), random.randrange(-500, -100),
                              random.choice(['hp', 'triple_laser', 'shield']))
            packages.append(package)
            package_counter += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        # Control Player Movement
        keys = pygame.key.get_pressed()
        def one_player_movement(keys):      # Preset keys for one player
            if keys[pygame.K_RIGHT] and player.x + player_vel + player.get_width < WIDTH:  # right
                player.x += player_vel
            if keys[pygame.K_UP] and player.y - player_vel > 0:  # up
                player.y -= player_vel
            if keys[pygame.K_DOWN] and player.y + player_vel + player.get_height + 20 < HEIGHT:  # down
                player.y += player_vel
            if keys[pygame.K_LEFT] and player.x - player_vel > 0:  # left
                player.x -= player_vel
            if keys[pygame.K_SPACE]:
                if player.cooldown_meter < player.ship_img.get_width():
                    if player.pack_flag['triple_shot']:
                        player.triple_shot()
                    else:
                        player.shoot()
            if not keys[pygame.K_SPACE]:
                if player.cooldown_meter >= 0:
                    player.cooldown_meter -= 0.6
        def two_player_movement(keys):      # Preset keys for two player
            # Blue Player
            if keys[pygame.K_RIGHT] and players[0].x + player_vel + players[0].get_width < WIDTH:  # right
                players[0].x += player_vel
            if keys[pygame.K_UP] and players[0].y - player_vel > 0:  # up
                players[0].y -= player_vel
            if keys[pygame.K_DOWN] and players[0].y + player_vel + players[0].get_height + 20 < HEIGHT:  # down
                players[0].y += player_vel
            if keys[pygame.K_LEFT] and players[0].x - player_vel > 0:  # left
                players[0].x -= player_vel
            if keys[pygame.K_l]:
                if players[0].cooldown_meter < players[0].ship_img.get_width():
                    if players[0].pack_flag['triple_shot']:
                        players[0].triple_shot()
                    else:
                        players[0].shoot()
            if not keys[pygame.K_l]:
                if players[0].cooldown_meter >= 0:
                    players[0].cooldown_meter -= 0.6
            # Orange Player2
            if keys[pygame.K_d] and players[1].x + player_vel + players[1].get_width < WIDTH:  # right
                players[1].x += player_vel
            if keys[pygame.K_w] and players[1].y - player_vel > 0:  # up
                players[1].y -= player_vel
            if keys[pygame.K_s] and players[1].y + player_vel + players[1].get_height + 20 < HEIGHT:  # down
                players[1].y += player_vel
            if keys[pygame.K_a] and players[1].x - player_vel > 0:  # left
                players[1].x -= player_vel
            if keys[pygame.K_g]:
                if players[1].cooldown_meter < players[1].ship_img.get_width():
                    if players[1].pack_flag['triple_shot']:
                        players[1].triple_shot()
                    else:
                        players[1].shoot()
            if not keys[pygame.K_g]:
                if players[1].cooldown_meter >= 0:
                    players[1].cooldown_meter -= 0.6

        if player2_flag:
            two_player_movement(keys)
        else:
            one_player_movement(keys)

        for pack in packages:
            pack.move(package_vel)
            for player in players:
                if collide(pack, player):
                    if pack.type == 'hp':
                        if player.health < 100:
                            player.health = 100
                            packages.remove(pack)
                            package_counter -= 1
                    if not player.pack_flag['triple_shot']:
                        if pack.type == 'triple_laser':
                            player.pack_flag['triple_shot'] = True
                            packages.remove(pack)
                            package_counter -= 1
                    if not player.pack_flag['shield']:
                        if pack.type == 'shield':
                            player.pack_flag['shield'] = True
                            packages.remove(pack)
                            package_counter -= 1
            if pack.y + pack.get_height > HEIGHT:
                packages.remove(pack)

        for enemy in enemies[:]:
            if isinstance(enemy, Boss):
                enemy.move()
            else:
                enemy.move(enemy_vel)
            if random.randrange(0, 70) == 1:
                enemy.shoot()
            enemy.move_lasers(laser_vel, players)
            for player in players:
                if collide(enemy, player):
                    if isinstance(enemy, Enemy):
                        player.health -= 15
                        enemies.remove(enemy)
                    else: lost = True           # player collided with boss
            if isinstance(enemy, Enemy) and enemy.y + enemy.get_height > HEIGHT:
                invades -= 1
                enemies.remove(enemy)
        for player in players:
            player.move_lasers(-(laser_vel), enemies)
# # # Game Loop # # #

main_font = pygame.font.SysFont("comicsans", 30)
def game_over(score):
    name = ""
    input_active = True
    prompt_text = main_font.render("Enter your name :", 1, (255, 255, 255))
    while input_active:
        input_text = main_font.render(name, 1, (255, 255, 255))
        WIN.blit(BG, (0, 0))
        WIN.blit(prompt_text, (WIDTH / 2 - prompt_text.get_width() / 2 - 200, 150))
        WIN.blit(input_text, (WIDTH / 2 - input_text.get_width() / 2, 150))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                else:
                    name += event.unicode
            pygame.display.update()
    save_score(name, score)
    display_scores()

def save_score(name, score):
    with open('scores.txt', 'a') as file:
        file.write(f"({name}, {score})\n")

def display_scores():
    try:
        with open('scores.txt', 'r') as file:
            scores = file.readlines()
        x_offset = 120
        y_offset = 100
        WIN.blit(BG, (0, 0))
        title_text = main_font.render("Scores List :", True, (255, 255, 0))
        return_to_menu = main_font.render("Press the mouse to return to menu", 1, (255, 255, 255))
        WIN.blit(title_text, (100, 50))
        WIN.blit(return_to_menu, (WIDTH/2 - return_to_menu.get_width()/2, HEIGHT-100))
        for score in scores:
            score_text = main_font.render(score.strip(), True, (255, 255, 255))
            WIN.blit(score_text, (x_offset, y_offset))
            y_offset += 40
            if y_offset > HEIGHT - 130:
                y_offset = 100
                x_offset += 200
        pygame.display.update()
        # Wait for user to close the window
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    #waiting = False
                    pygame.quit()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False
                    main_menu()
    except FileNotFoundError:
        no_scores_text = main_font.render("No scores saved yet.", True, (255, 255, 255))
        WIN.blit(no_scores_text, (250, 250))
        pygame.display.flip()
        return

def instructions_screen(players):
    instructions_font = pygame.font.SysFont("comicsans", 24)
    instruction_3 = instructions_font.render("~ Destroy all enemies before they invade your planet ! ~", 1,
                                             (255, 255, 255))
    instruction_4 = instructions_font.render("Press the mouse the begin...", 1, (255, 255, 255))
    instructions_flag = True
    if players == 1:
        instruction_1 = instructions_font.render("~ Use Arrows to move the spaceship ~", 1, (255, 255, 255))
        instruction_2 = instructions_font.render("~ Press Spacebar to shoot lasers ~", 1, (255, 255, 255))
    if players == 2:
        instruction_1 = instructions_font.render("Player 1 : Use Arrows to move the spaceship, Press L to Shoot Lasers", 1, (65, 105, 255))
        instruction_2 = instructions_font.render("Player 2 : Use W,S,A,D to move the spaceship, Press G to Shoot Lasers", 1, (255,140,0))
    while instructions_flag:
        WIN.blit(BG, (0, 0))
        if players == 1:
            WIN.blit(instruction_1, (WIDTH / 2 - instruction_2.get_width() / 2 -35, 300))
            WIN.blit(instruction_2, (WIDTH / 2 - instruction_1.get_width() / 2, 400))
        else:
            WIN.blit(instruction_1, (WIDTH / 2 - instruction_2.get_width() / 2, 300))
            WIN.blit(instruction_2, (WIDTH / 2 - instruction_1.get_width() / 2 -10, 400))
        WIN.blit(instruction_3, (WIDTH / 2 - instruction_3.get_width() / 2 -15, 500))
        WIN.blit(instruction_4, (WIDTH / 2 - instruction_4.get_width() / 2 -20, 600))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                instructions_flag = False
                pygame.quit()
                return  # Exit the function entirely
            if event.type == pygame.MOUSEBUTTONDOWN:
                pygame.mixer.music.play(-1)
                main()
                return


def main_menu():
    global player2_flag
    title_font = pygame.font.SysFont("comicsans", 30)
    button_font = pygame.font.SysFont("comicsans", 20)
    run = True
    # Define button dimensions and positions
    button_width = 200
    button_height = 50
    button_y = 500
    button1_x = WIDTH // 2 - button_width - 20
    button2_x = WIDTH // 2 + 20
    while run:
        WIN.blit(BG, (0, 0))
        title_label1 = title_font.render("Welcome to Space Invaders Pro !!!", 1, (255, 255, 255))
        WIN.blit(title_label1, (WIDTH / 2 - title_label1.get_width() / 2 - 20, 300))
        title_label2 = title_font.render("Choose number of players...", 1, (255, 255, 255))
        WIN.blit(title_label2, (WIDTH / 2 - title_label1.get_width() / 2 + 30, 400))
        # Create and render buttons
        pygame.draw.rect(WIN, (100, 100, 100), (button1_x, button_y, button_width, button_height))
        pygame.draw.rect(WIN, (100, 100, 100), (button2_x, button_y, button_width, button_height))

        single_player_text = button_font.render("1 Player", 1, (255, 255, 255))
        two_player_text = button_font.render("2 Players", 1, (255, 255, 255))

        WIN.blit(single_player_text, (button1_x + button_width // 2 - single_player_text.get_width() // 2,
                                   button_y + button_height // 2 - single_player_text.get_height() // 2))
        WIN.blit(two_player_text, (button2_x + button_width // 2 - two_player_text.get_width() // 2,
                                   button_y + button_height // 2 - two_player_text.get_height() // 2))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                # Start 1 player game
                if button1_x <= mouse_pos[0] <= button1_x + button_width and button_y <= mouse_pos[1] <= button_y + button_height:
                    instructions_screen(1)
                    run = False
                # Start 2 player game
                elif button2_x <= mouse_pos[0] <= button2_x + button_width and button_y <= mouse_pos[1] <= button_y + button_height:
                    player2_flag = True
                    instructions_screen(2)
                    run = False
    pygame.quit()

if __name__ == "__main__":
    try:
        main_menu()
    except pygame.error:
        pass  # Ignore Pygame errors when closing
    finally:
        pygame.quit()
