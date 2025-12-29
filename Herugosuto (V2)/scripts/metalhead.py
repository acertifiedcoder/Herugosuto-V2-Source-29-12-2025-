from scripts.entity import Entity
from scripts.core_funcs import *
from scripts.projectiles import Projectile

import random
import math

class MetalHead(Entity):
    def __init__(self, *args):
        super().__init__(*args)
        self.velocity = [0, 0]
        self.bob_timer = 0
        self.hover_distance = random.randint(50, 90)
        self.speed = random.randint(50, 80)
        self.hover_rate = 2
        self.attack_timer = 0

    def update(self, dt):
        super().update(dt)
        self.bob_timer += dt
        self.attack_timer -= dt

        self.velocity[0] = normalize(self.velocity[0], 250 * dt)
        self.velocity[1] = normalize(self.velocity[1], 250 * dt)
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt

        player = self.game.player
        angle = self.get_angle(player)
        target_position = [player.pos[0] + math.cos(angle + math.pi) * self.hover_distance, player.pos[1] + math.sin(angle + math.pi) * self.hover_distance]
        target_position[1] += math.sin(self.bob_timer) * 16

        target_angle = self.get_angle(target_position)
        if self.get_distance(target_position) > self.speed * dt:
            self.pos[0] += math.cos(target_angle) * self.speed * dt
            self.pos[1] += math.sin(target_angle) * self.speed * dt
        else:
            self.pos = target_position.copy()

        if self.get_distance(player.center) < 120:
            if self.attack_timer < 0:
                self.game.projectiles.append(Projectile('heavy_blob', self.center.copy(), angle, 200, self.game, self))
                self.attack_timer = 1 