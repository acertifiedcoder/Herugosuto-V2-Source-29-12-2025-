import random
import pygame
import math

def itr(l):
    return sorted(enumerate(l), reverse=True)

def normalize(num, amt):
    if num > amt:
        num -= amt
    elif num < -amt:
        num += amt
    else:
        num = 0
    return num

def swap_color(img, old_c, new_c):
    img.set_colorkey(old_c)
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img, (0, 0))
    surf.set_colorkey((0, 0, 0))
    return surf

def blit_center(target_surf, surf, loc):
    target_surf.blit(surf, (loc[0] - surf.get_width() // 2, loc[1] - surf.get_height() // 2))

# def tile_collide(pos, tile_size, map):
#     tile_pos = (int(pos[0] // tile_size[0]), int(pos[1] // tile_size[1]))
#     if tile_pos in map:
#         return True
#     else:
#         return False

class ParticleManager:
    def __init__(self):
        self.particle_groups = {}

    def add_particles(self, group, *args, **kwargs):
        if group not in self.particle_groups:
            self.particle_groups[group] = []
        self.particle_groups[group].append(Particle(*args, **kwargs))

    def render(self, group, surf, offset=(0, 0)):
        if group in self.particle_groups:
            for particle in self.particle_groups[group]:
                particle.draw(surf, offset)

    def update(self):
        for group in self.particle_groups:
            for i, particle in itr(self.particle_groups[group]):
                alive = particle.update()
                if not alive:
                    self.particle_groups[group].pop(i)

class Particle:

    def __init__(self, pos, particle_type, motion, decay_rate, start_frame, game_map, particle_images, global_time, physics=None, custom_color=None):
        self.pos = list(pos)
        self.type = particle_type
        self.motion = list(motion)
        self.decay_rate = decay_rate
        self.color = custom_color
        self.frame = start_frame
        self.physics = physics
        self.orig_motion = self.motion
        self.temp_motion = [0, 0]
        self.particle_images = particle_images
        self.time_left = len(self.particle_images[self.type]) + 1 - self.frame
        self.render = True
        self.random_constant = random.randint(20, 30) / 30
        self.rotation = 0
        self.global_time = global_time
        self.random_constant = random.randint(20, 30) / 30

        if game_map != []:
            self.game_map = game_map
        else:
            self.game_map = []

    def draw(self,surface,scroll):
        if self.render:
            img = self.particle_images[self.type][int(self.frame)]
            if self.color:
                img = swap_color(img, (255, 255, 255), self.color)
            if self.rotation:
                img = pygame.transform.rotate(img, self.rotation)
            blit_center(surface, img, (self.pos[0] - scroll[0], self.pos[1] - scroll[1]))

    def update(self, physics=None):
        self.frame += self.decay_rate
        self.time_left = len(self.particle_images[self.type]) + 1 - self.frame
        running = True
        self.render = True
        if self.frame >= len(self.particle_images[self.type]):
            self.render = False
            if self.frame >= len(self.particle_images[self.type]) + 1:
                running = False
            running = False

        if self.type in ["shells", "mag", "shotgun_shells", "clip", "p90", "smg", "uzi", "hornet"]:
            abs_motion = (abs(self.motion[1]) + abs(self.motion[0]))
            self.motion[1] += 0.4
            if abs_motion > 0.1:
                self.rotation += 2 * abs_motion

        if self.type in ['p_terrain']:
            self.temp_motion[0] += (math.sin(self.global_time * 3 + (self.random_constant - 0.67) * 10) * 10) * (1 / 60)
            self.motion[0] = max(self.motion[0] - 10 * (1 / 60), -80)
            self.motion[1] = min(self.motion[0] + 200 * (1 / 60), 120)

        if not self.physics:
            self.pos[0] += (self.temp_motion[0] + self.motion[0])
            self.pos[1] += (self.temp_motion[1] + self.motion[1])
        else:
            self.pos[0] += (self.temp_motion[0] + self.motion[0])
            hit = False
            if self.game_map.tile_collide(self.pos):
                self.motion[0] *= -0.7
                self.motion[1] *= 0.8
                hit = True
            self.pos[1] += (self.temp_motion[1] + self.motion[1])
            if self.game_map.tile_collide(self.pos):
                self.motion[1] *= -0.7
                self.motion[0] *= 0.8
                hit = True
            if hit:
                self.pos[0] += (self.temp_motion[0] + self.motion[0]) * 2
                self.pos[1] += (self.temp_motion[1] + self.motion[1]) * 2
        self.temp_motion = [0, 0]
        return running
