from scripts.config import config
from scripts.core_funcs import *
import math
import pygame
import random

class Projectile:
    def __init__(self, type, pos, rot, speed, game, owner):
        self.game = game
        self.type = type
        self.pos = pos
        self.rotation = rot
        self.speed = speed
        self.config = config["projectiles"][self.type]
        self.owner = owner

        advance(self.pos, self.rotation, self.config['spawn_advance'])

    def move(self, dt):
        directions = {k: False for k in ['top', 'left', 'right', 'bottom']}
        cx = math.cos(self.rotation) * self.speed * dt
        self.pos[0] += cx
        if self.game.level_map.tile_collide(self.pos):
            if cx > 0:
                directions['right'] = True
            else:
                directions['left'] = True
            return directions

        cy = math.sin(self.rotation) * self.speed * dt
        self.pos[1] += cy
        if self.game.level_map.tile_collide(self.pos):
            if cy > 0:
                directions['bottom'] = True
            else:
                directions['top'] = True
        return directions

    def update(self, dt):
        if not self.game.player.in_range(self, 600):
            return False

        if self.config['group'] == 'heavy_blob':
            vec = to_cart(self.rotation, self.speed)
            vec[1] = min(200, vec[1] + dt * 200)
            self.rotation, self.speed = to_polar(vec)
        
        collisions = self.move(dt)
        if any(collisions.values()):
            if self.config['group'] == 'normal':
                if collisions['top']:
                    angle = math.pi * 3 / 2
                if collisions['bottom']:
                    angle = math.pi / 2
                if collisions['right']:
                    angle = 0
                if collisions['left']:
                    angle = math.pi
                for i in range(random.randint(2, 3)):
                    self.game.vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), angle)
                return False
            elif self.config['group'] == "heavy_blob":
                vec = to_cart(self.rotation, self.speed)
                if collisions['top']:
                    vec[1] *= -1
                if collisions['bottom']:
                    vec[1] *= -1
                if collisions['right']:
                    vec[0] *= -1
                if collisions['left']:
                    vec[0] *= -1
                self.rotation, self.speed = to_polar(vec)
                advance(self.pos, self.rotation, self.config['spawn_advance'])
                for i in range(random.randint(2, 3)):
                    self.game.vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), self.rotation)

        for entity in self.game.entities:
            if entity != self.owner:
                if entity.rect.collidepoint(self.pos):
                    entity.velocity[0] += math.cos(self.rotation) * self.config['knockback']
                    entity.velocity[1] += math.sin(self.rotation) * self.config['knockback']
                    for i in range(random.randint(15, 30)):
                        self.game.vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), self.rotation)
                    return False

        return True

    def render(self, surf, offset=(0, 0)):
        render_pos = [self.pos[0] - offset[0], self.pos[1] - offset[1]]
        if self.config['shape']:
            if self.config['shape'][0] == 'line':
                pygame.draw.line(surf, self.config['shape'][1], render_pos, advance(render_pos.copy(), self.rotation, self.config['shape'][2]), self.config['shape'][3])
        else:
            img = self.game.projectile_images[self.type]
            render_pos[0] -= img.get_width()
            render_pos[1] -= img.get_height()
            surf.blit(img, render_pos)