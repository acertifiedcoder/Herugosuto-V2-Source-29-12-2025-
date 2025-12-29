import pygame
import math
import random
import time

from scripts.item import Item
from scripts.config import config
from scripts.core_funcs import *
from scripts.projectiles import Projectile

class Weapon(Item):
    def __init__(self, game, owner, type, amount=1):
        super().__init__(game, owner, type, amount)
        self.rotation = 0
        self.capacity = config['weapons'][self.type]['capacity']
        self.ammo = self.capacity
        self.ammo_type = config['weapons'][self.type]['ammo_type']
        self.projectile_type = config['weapons'][self.type]['projectile_type']
        self.reload_method = config['weapons'][self.type]['reload']
        self.attack_rate = config['weapons'][self.type]['attack_rate']
        self.controls = config['weapons'][self.type]['controls']
        self.last_attack = 0

    def reload(self):
        if (self.ammo < self.capacity) and (self.owner.ammo[self.ammo_type] > 0):
            dif = min(self.owner.ammo[self.ammo_type], self.capacity - self.ammo)
            self.ammo += dif
            self.owner.ammo[self.ammo_type] -= dif

            if self.reload_method == "shells":
                for i in range(dif):
                    self.game.particles.add_particle('foreground', self.owner.pos, 'shells', [(self.owner.flip[0] - 0.5) * random.randint(30, 110), -random.randint(70, 110)], 0.1, 0, custom_color=(246, 255, 0), physics=self.game.level_map)
            if self.reload_method == "mag":
                self.game.particles.add_particle('foreground', self.owner.pos, 'mag', [(self.owner.flip[0] - 0.5) * random.randint(30, 110), -random.randint(70, 110)], 0.1, 0, physics=self.game.level_map)  
            if self.reload_method == "vector_mag":
                self.game.particles.add_particle('foreground', self.owner.pos, 'vector_mag', [(self.owner.flip[0] - 0.5) * random.randint(30, 110), -random.randint(70, 110)], 0.1, 0, physics=self.game.level_map)     

    def attack(self):
        if (self.ammo > 0) and (time.time() - self.last_attack > self.attack_rate):
            self.ammo -= 1
            self.last_attack = time.time()
            self.game.projectiles.append(Projectile(self.projectile_type, self.owner.center.copy(), math.radians(self.rotation), 300, self.game, self.owner))
            self.game.vfx.spawn_group('bow_sparks', advance(self.owner.center.copy(), math.radians(self.rotation), 22), math.radians(self.rotation))
            if self.reload_method in ['mag', 'vector_mag']:
                self.game.particles.add_particle('foreground', self.owner.pos, 'shells', [(self.owner.flip[0] - 0.5) * random.randint(30, 110), -random.randint(70, 110)], 0.1, 0, custom_color=(246, 255, 0), physics=self.game.level_map)

    def render(self, surf, loc):
        img = self.game.weapons[self.type].copy()
        if (self.rotation % 360 < 270) and (self.rotation % 360 > 90):
            img = pygame.transform.flip(img, False, True)
        img = pygame.transform.rotate(img, -self.rotation)
        surf.blit(img, (loc[0] - img.get_width() // 2, loc[1] - img.get_height() // 2))