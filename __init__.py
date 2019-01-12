import ugfx
import badge
import random
import sys

EMULATOR = False
DEBUG = True
try:
    import easydraw
    import appglue
except ImportError:
    print("Badge emulator detected, disabling some features")
    EMULATOR = True

import time


level1 = {
    "planes": {
        "1": {"hp": 1, "count": 1, "damage": 1, "rate": 0.05, "shoot_chance" : 0.001, "move_chance": 0.005}
        #"1": {"hp": 1, "count": 3, "damage": 1, "rate": 0.05, "shoot_chance" : 0.01, "move_chance": 0.01}
        #"1": {"hp": 5, "count": 7, "damage": 1, "rate": 0.05},
        #"2": {"hp": 15, "count": 3, "damage": 1, "rate": 0.02},
    }
}
level2 = {
    "planes": {
        "1": {"hp": 3, "count": 10, "damage": 1, "rate": 0.05, "shoot_chance" : 0.001, "move_chance": 0.005},
        "2": {"hp": 10, "count": 3, "damage": 10, "rate": 0.02, "shoot_chance" : 0.05, "move_chance": 0.0001},
    }
}
levels = [level1, level2]

PLANE_PLAYER = 0
PLANE_ENEMY = 1
DIRECTION_LEFT = 0
DIRECTION_RIGHT = 1
DIRECTION_UP = 2
DIRECTION_DOWN = 3
MIN_X = int(0)
MAX_X = int(15)
MIN_Y = int(0)
MAX_Y = int(10)

SCREEN_X = int(293)
SCREEN_Y = int(126)

MESSAGE_X = 60
MESSAGE_Y = 60

X_SIZE = int(SCREEN_X / (MAX_X + 1)) + 1
Y_SIZE = int(SCREEN_Y / (MAX_Y + 1))


def message(message):
    ugfx.string(MESSAGE_X, MESSAGE_Y, message, "Roboto_BlackItalic20", ugfx.WHITE)


def buzzer(freq, duration):
    if not EMULATOR:
        badge.buzzer(freq, duration)
    else:
        print("Emulator: buzz disabled")


def home():
    if not EMULATOR:
        appglue.home()
    else:
        print("Emulator: home() does nothing")


class Plane:
    x = 0
    y = 0
    hp = 0
    plane_type = 0
    damage = 1

    def handle_hit(self, missile):
        self.hp -= missile.damage
        buzzer(5000, 0.05)
        if self.hp <= 0:
            return True
        return False


class EnemyPlane(Plane):
    plane_type = PLANE_ENEMY

    def draw(self):
        # Draws from the x, y location of the plan so that
        # X is in the left of plane
        # and Y is to highest pixel.
        width = 8
        height = 12
        x = int(self.x * X_SIZE)
        y = int(self.y * Y_SIZE)
        ugfx.line(int(x + width/2), y, int(x), y + height, ugfx.WHITE)
        ugfx.line(int(x + width/2), y, int(x + width), y + height, ugfx.WHITE)
        ugfx.line(int(x + width), y + height, int(x), y + height, ugfx.WHITE)


class PlayerPlane(Plane):
    plane_type = PLANE_PLAYER
    hp = 10
    y = MAX_Y
    damage = 1

    def draw(self):
        # Draws from the x, y location of the plan so that
        # X is in the left of plane
        # and Y is to highest pixel.
        width = 8
        height = 12
        x = self.x * X_SIZE
        y = self.y * Y_SIZE
        ugfx.line(int(x + width/2), y, int(x), y + height, ugfx.WHITE)
        ugfx.line(int(x + width/2), y, int(x + width), y + height, ugfx.WHITE)
        ugfx.line(int(x + width), y + height, int(x), y + height, ugfx.WHITE)


class Missile:
    x = 0
    y = 0
    direction = DIRECTION_UP
    damage = 1

    def step(self):
        if self.direction == DIRECTION_UP:
            self.y -= 1
        elif self.direction == DIRECTION_DOWN:
            self.y += 1
        else:
            raise Exception("Unknown direction")

    def draw(self):
        width = 4
        height = 8
        x = self.x * X_SIZE
        y = self.y * Y_SIZE
        # center
        ugfx.line(x + int(X_SIZE/2), y, int(x + X_SIZE/2), y + height, ugfx.WHITE)
        if self.direction == DIRECTION_UP:
            # left pix
            ugfx.line(x + int(X_SIZE / 2) - 1, y + 3, int(x + X_SIZE / 2) - 1, y + height, ugfx.WHITE)
            # right pix
            ugfx.line(x + int(X_SIZE / 2) + 1, y + 3, int(x + X_SIZE / 2) + 1, y + height, ugfx.WHITE)
        elif self.direction == DIRECTION_DOWN:
            # left pix
            ugfx.line(x + int(X_SIZE / 2) - 1, y, int(x + X_SIZE / 2) - 1, y + height - 3, ugfx.WHITE)
            # right pix
            ugfx.line(x + int(X_SIZE / 2) + 1, y, int(x + X_SIZE / 2) + 1, y + height - 3, ugfx.WHITE)
        else:
            raise Exception("Unsupported direction")


class Game:
    player_plane = None
    enemy_planes = []
    missiles = []
    level = 0

    def __init__(self):
        self.is_running = True
        self.player_plane = PlayerPlane()
        self.planes_spawned = {}

    def init_level(self):
        self.player_plane.x = 10
        self.player_plane.y = 10

    def dead(self):
        message("YOU ARE DEAD")
        time.sleep(5)
        self.is_running = False

    def check_hits(self):
        remove_planes = []
        remove_missiles = []
        for missile in self.missiles:
            for enemy in self.enemy_planes:
                if missile.x == enemy.x and missile.y == enemy.y:
                    print("Enemy hit!")
                    buzzer(500, 0.05)
                    if enemy.handle_hit(missile):
                        remove_planes.append(enemy)
                    remove_missiles.append(missile)
            if missile.x == self.player_plane.x and missile.y == self.player_plane.y:
                if self.player_plane.handle_hit(missile):
                    self.dead()
                    return
                remove_missiles.append(missile)

            if missile.y < MIN_Y or missile.y > MAX_Y:
                remove_missiles.append(missile)

        for plane in remove_planes:
            if plane in self.enemy_planes:
                self.enemy_planes.remove(plane)

        for missile in remove_missiles:
            if missile in remove_missiles:
                self.missiles.remove(missile)

    def spawn_plane(self, plane_info, plane_type):
        plane = EnemyPlane()
        plane.y = 0
        plane.x = random.randint(MIN_X, MAX_X)
        plane.shoot_chance = plane_info["shoot_chance"]
        plane.move_chance = plane_info["move_chance"]

        # Perform a duplicate check and fail spawn if plane already exists
        for check in self.enemy_planes:
            if check.x == plane.x and check.y == plane.y:
                print("Spot is blocked, failing spawn")
                return False
        plane.hp = plane_info["hp"]
        plane.damage = plane_info["damage"]
        self.enemy_planes.append(plane)

        if plane_type in self.planes_spawned:
            self.planes_spawned[plane_type] += 1
        else:
            self.planes_spawned[plane_type] = 1

        print("Spawned a plane of type %s" % plane_type)
        return True

    def check_spawn(self):
        # Check if we should spawn more enemies
        for plane_type, plane_info in self.level["planes"].items():
            planes_left = plane_info["count"]
            if plane_type in self.planes_spawned:
                planes_left -= self.planes_spawned[plane_type]
            if planes_left > 0:
                # Roll a dice
                dice = random.uniform(0, 1)
                if dice <= plane_info["rate"]:
                    print("Spawning a plane")
                    self.spawn_plane(plane_info, plane_type)

    def next_level(self):
        self.level_n += 1
        self.enemy_planes.clear()
        self.planes_spawned.clear()
        if self.level_n == 0:
            # First level
            pass
        elif self.level_n >= len(levels):
            for n in range(50):
                ugfx.clear(ugfx.BLACK)
                message("You've won the game! :)")
                ugfx.flush()
                buzzer(8000, 0.1)
                buzzer(4000, 0.1)
                time.sleep(0.1)
            self.is_running = False
            return
        else:
            for n in range(5):
                ugfx.clear(ugfx.BLACK)
                message("You've cleared level %s/%s" % (self.level_n, len(levels),))
                ugfx.flush()
                buzzer(5000, 0.1)
                time.sleep(0.1)

        self.level = levels[self.level_n]

    def check_level_win(self):
        # Check if player has cleared the level
        total_left = 0
        for plane_type, plane_info in self.level["planes"].items():
            spawned_count = 0
            if plane_type in self.planes_spawned:
                spawned_count = self.planes_spawned[plane_type]
            planes_left = plane_info["count"] - spawned_count
            total_left += planes_left

        total_left += len(self.enemy_planes)
        print("total_left: %s" % total_left)
        if total_left <= 0:
            self.next_level()

    def draw(self):
        ugfx.clear(ugfx.BLACK)

        for missile in self.missiles:
            missile.draw()

        for plane in self.enemy_planes:
            plane.draw()

        self.player_plane.draw()

    def check_enemy_moves(self):
        for enemy in self.enemy_planes:
            dice = random.uniform(0, 1)
            if dice >= enemy.shoot_chance:
                print("enemy shoots")
                self.enemy_shoot(enemy)
            if dice >= enemy.move_chance:
                print("enemy moves")
                self.enemy_move(enemy)

    def enemy_shoot(self, enemy):
        print("Enemy shot a missile")
        missile = Missile()
        missile.x = enemy.x
        missile.y = enemy.y + 1
        missile.damage = enemy.damage
        missile.direction = DIRECTION_DOWN
        self.missiles.append(missile)

    def get_move_coords(self, plane, direction):
        # Returns a tuple of coordinates (x, y)
        if direction == DIRECTION_DOWN:
            return plane.x, plane.y + 1
        elif direction == DIRECTION_UP:
            return plane.x, plane.y - 1
        elif direction == DIRECTION_RIGHT:
            return plane.x + 1, plane.y
        elif direction == DIRECTION_LEFT:
            return plane.x - 1, plane.y
        else:
            raise Exception("Unknown direction %s" % (direction,))

    def enemy_move(self, enemy):
        # Try to move the enemy 5 times, ignoring spots with other enemies
        for t in range(5):
            direction = random.randint(0, 3)
            x, y = self.get_move_coords(enemy, direction)
            if x < MIN_X or x > MAX_X or y < MIN_Y or y > MAX_Y:
                continue

            # Coords look valid, now do a dupe check for other enemies
            dupe = False
            for e in self.enemy_planes:
                if x == e.x and y == e.y:
                    dupe = True
                    break

            if dupe:
                continue

            print("Moving enemy")
            enemy.x = x
            enemy.y = y
        print("Move failed")

    def game_loop(self):
        self.level_n = -1
        turn = 0
        self.next_level()
        self.planes_spawned = {}
        while self.is_running:
            time.sleep(0.05)
            turn += 1
            if turn % 13 == 0:
                # Missile speed is 1/13 of tickrate
                for missile in self.missiles:
                    missile.step()
                self.check_hits()
                self.check_level_win()
                self.check_enemy_moves()

            self.check_spawn()

            # Draw every turn
            self.draw()

    def move(self, direction):
        if direction == DIRECTION_LEFT:
            print("LEFT")
            self.player_plane.x -= 1
            if self.player_plane.x < MIN_X:
                self.player_plane.x = MIN_X
        elif direction == DIRECTION_RIGHT:
            print("RIGHT")
            self.player_plane.x += 1
            if self.player_plane.x > MAX_X:
                self.player_plane.x = MAX_X
        else:
            raise Exception("Unknown direction")

    def shoot(self):
        print("Shoot from x=%s y=%s" % (self.player_plane.x, self.player_plane.y))
        missile = Missile()
        missile.x = self.player_plane.x
        missile.y = self.player_plane.y - 1
        missile.direction = DIRECTION_UP
        self.missiles.append(missile)
        missile.draw()
        buzzer(3000, 0.1)

    def badge_init(self):
        badge.init()
        ugfx.init()
        ugfx.input_init()
        ugfx.input_attach(ugfx.BTN_B, lambda pushed: home() if pushed else False)
        ugfx.input_attach(ugfx.BTN_START, lambda pushed: self.shoot() if pushed else False)
        ugfx.input_attach(ugfx.JOY_UP, lambda pushed: print("JOY_UP") if pushed else False)
        ugfx.input_attach(ugfx.JOY_DOWN, lambda pushed: print("JOY_DOWN") if pushed else False)
        ugfx.input_attach(ugfx.JOY_RIGHT, lambda pushed: self.move(DIRECTION_RIGHT) if pushed else False)
        ugfx.input_attach(ugfx.JOY_LEFT, lambda pushed: self.move(DIRECTION_LEFT) if pushed else False)

    def test_draw(self):
        while True:
            ugfx.clear(ugfx.BLACK)
            #ugfx.line(0, 0, 293, 0, ugfx.WHITE)
            #ugfx.line(20, 0, 20, 126, ugfx.WHITE)
            ugfx.flush()

    def splash(self):
        ugfx.clear(ugfx.BLACK)
        for n in range(3):
            ugfx.string(40, 40, "Fighter", "Roboto_BlackItalic24", ugfx.WHITE)
            ugfx.string(45, 65, "@ Disobey2019", "Roboto_BlackItalic20", ugfx.WHITE)
            ugfx.string(20, 90, "https://github.com/mkorkalo/disobeyfighter", "Roboto_BlackItalic20", ugfx.WHITE)
            ugfx.flush()
            buzzer(1000, 0.1)
            time.sleep(1)

    def run(self):
        self.badge_init()
        #self.splash()
        #self.test_draw()
        self.init_level()
        self.game_loop()


while True:
    game = Game()
    try:
        game.run()
    except Exception as ex:
        print(ex)
        print(repr(sys.exc_info()))
        #traceback.print_tb()
