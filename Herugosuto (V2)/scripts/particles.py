import os
import random

import pygame

from scripts.core_funcs import *

class ParticleManager:
    def __init__(self, game):
        self.game = game
        self.particle_groups = {}

    def add_particle(self, group, *args, **kwargs):
        if group not in self.particle_groups:
            self.particle_groups[group] = []
        self.particle_groups[group].append(Particle(self.game, *args, **kwargs))

    def render(self, group, surf, offset=(0, 0)):
        if group in self.particle_groups:
            for particle in self.particle_groups[group]:
                particle.draw(surf, offset)

    def update(self):
        dt = self.game.dt
        for group in self.particle_groups:
            for i, particle in itr(self.particle_groups[group]):
                alive = particle.update(dt)
                if not alive:
                    self.particle_groups[group].pop(i)

class Particle():
    def __init__(self, game, pos, particle_type, motion, decay_rate, start_frame, physics=None, custom_color=None):
        self.game = game
        self.pos = list(pos)
        self.type = particle_type
        self.motion = list(motion)
        self.decay_rate = decay_rate
        self.color = custom_color
        self.frame = start_frame
        self.physics = physics
        self.orig_motion = self.motion
        self.temp_motion = [0, 0]
        self.time_left = len(self.game.particle_images[self.type]) + 1 - self.frame
        self.render = True
        self.random_constant = random.randint(20, 30) / 30
        self.time_alive = 0
        self.rotation = 0

    def draw(self, surface, scroll):
        if self.render:
            img = self.game.particle_images[self.type][int(self.frame)].copy()
            if self.color:
                img = swap_color(img, (255, 255, 255), self.color)
            if self.rotation:
                img = pygame.transform.rotate(img, self.rotation)
            blit_center(surface, img, (self.pos[0]-scroll[0],self.pos[1]-scroll[1]))

    def update(self, dt):
        self.time_alive += dt
        self.frame += self.decay_rate * dt
        self.time_left = len(self.game.particle_images[self.type]) + 1 - self.frame
        running = True

        self.render = True
        if self.frame >= len(self.game.particle_images[self.type]):
            self.render = False
            if self.frame >= len(self.game.particle_images[self.type]) + 1:
                running = False
            running = False

        if self.type in ["shells", "mag", "vector_mag"]:
            # self.motion[0] = normalize(self.motion[0], 20 * dt)
            abs_motion = (abs(self.motion[1]) + abs(self.motion[0]))
            self.motion[1] += 300 * dt
            if abs_motion > 10:
                self.rotation += 20 * dt * abs_motion

        if not self.physics:
            self.pos[0] += (self.temp_motion[0] + self.motion[0]) * dt
            self.pos[1] += (self.temp_motion[1] + self.motion[1]) * dt
        else:
            self.pos[0] += (self.temp_motion[0] + self.motion[0]) * dt
            hit = False
            if self.physics.tile_collide(self.pos):
                self.motion[0] *= -0.7
                self.motion[1] *= 0.8
                hit = True
                # self.pos[0] += (self.temp_motion[0] + self.motion[0]) * dt
            self.pos[1] += (self.temp_motion[1] + self.motion[1]) * dt
            if self.physics.tile_collide(self.pos):
                self.motion[1] *= -0.7
                self.motion[0] *= 0.8
                hit = True
                # self.pos[1] += (self.temp_motion[1] + self.motion[1]) * dt
            if hit:
                self.pos[0] += (self.temp_motion[0] + self.motion[0]) * dt * 2
                self.pos[1] += (self.temp_motion[1] + self.motion[1]) * dt * 2
        self.temp_motion = [0, 0]
        return running
