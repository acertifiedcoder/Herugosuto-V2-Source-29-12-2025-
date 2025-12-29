import pygame

from scripts.core_funcs import *

class DestructionParticles:
    def __init__(self, game):
        self.game = game
        self.particles = []

    def add_particle(self, surf, loc, velocity, duration=5, rotation=0, gravity=True):
        particle_data = {
            "surf": surf,
            "loc": loc,
            "vel": velocity,
            "duration": duration,
            "rotation": rotation,
            'stationary': False
        }
        self.particles.append(particle_data)
        self.gravity = gravity

    def update(self):
        for i, particle in itr(self.particles):
            hit = False
            if not particle['stationary']:
                particle['loc'][0] += (particle['vel'][0])
                if self.game.level_map.tile_collide(particle['loc']):
                    particle['vel'][0] *= -0.4
                    particle['vel'][1] *= 0.8
                    particle['vel'][2] *= 0.5
                    hit = True
                particle['loc'][1] += (particle['vel'][1])
                if self.game.level_map.tile_collide(particle['loc']):
                    particle['vel'][1] *= -0.4
                    particle['vel'][0] *= 0.8
                    particle['vel'][2] *= 0.5
                    hit = True
                if hit:
                    if abs(particle['vel'][0]) + abs(particle['vel'][1]) < 1:
                        particle['stationary'] = True
                    else:
                        particle['loc'][0] += (particle['vel'][0]) * 4
                        particle['loc'][1] += (particle['vel'][1]) * 4

                particle['rotation'] += particle['vel'][2]
                if self.gravity:
                    particle['vel'][1] += 10 * (1 / 60)

            particle['duration'] -= 0.006
            if particle['duration'] < 0:
                self.particles.pop(i)

    def render(self, surf, offset=(0, 0)):
        for particle in self.particles:
            blit_center(surf, pygame.transform.rotate(particle['surf'].copy(), particle['rotation']), (particle['loc'][0] - offset[0], particle['loc'][1] - offset[1]))
