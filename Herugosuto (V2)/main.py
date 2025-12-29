import sys
import pygame
import random
import time
import math
import os

from pygame.locals import *

import scripts.tile_map as tile_map
import scripts.spritesheet_loader as spritesheet_loader
from scripts.foliage import AnimatedFoliage
from scripts.entity import Entity
from scripts.anim_loader import AnimationManager
from scripts.grass import GrassManager
from scripts.foliage import AnimatedFoliage
from scripts.text import Font
from scripts.particles import ParticleManager
from scripts.core_funcs import *
from scripts.weapon import Weapon
from scripts.projectiles import Projectile
from scripts.vfx import VFX
from scripts.metalhead import MetalHead
from scripts.weapons import create_weapon
from scripts.hitboxes import Hitboxes
from scripts.destruction_particles import DestructionParticles

# freeze? test -- should be moved to its own camera thingy
freeze_frame = {}
def add_freeze(rate, duration):
    time.sleep(0.05)
    freeze_frame[rate] = duration

# camera stuff prob make a seperate file with in depth camera attributes and stuff
class Camera:
    def __init__(self, game):
        self.game = game
        self.true_pos = [0, 0]
        self.target_pos = [0, 0]
        self.rate = 0.18
        self.track_entity = None

    def set_tracked_entity(self, entity):
        self.track_entity = entity

    def set_target(self, pos):
        self.target_pos = list(pos)

    def update(self):
        if self.track_entity:
            self.set_target((self.track_entity.pos[0] - self.game.display.get_width() // 2, self.track_entity.pos[1] - self.game.display.get_height() // 2))

        self.true_pos[0] += (self.target_pos[0] - self.true_pos[0]) / (self.rate / self.game.dt)
        self.true_pos[1] += (self.target_pos[1] - self.true_pos[1]) / (self.rate / self.game.dt)

    @property
    def render_offset(self):
        return [self.true_pos[0] - self.game.window_offset[0], self.true_pos[1] - self.game.window_offset[1]]

    @property
    def pos(self):
        return (int(math.floor(self.true_pos[0])), int(math.floor(self.true_pos[1])))

class GameData:
    def __init__(self):
        pygame.mouse.set_visible(False)
        self.start_time = time.time()
        # self.frame_start()
        self.reset()

        # image loading gon be moved to an assets file
        self.misc = load_dir('data/images/misc')
        self.weapons = load_dir('data/images/weapons')
        self.particle_images = {folder: load_dir_list('data/images/particles/' + folder) for folder in os.listdir('data/images/particles')}

        self.window_offset = [192, 100]
        self.display = pygame.Surface((640, 360))

        self.camera = Camera(self)
        self.animations = AnimationManager()

        self.vfx = VFX(self)
        self.particles = ParticleManager(self)
        self.destruction_particles = DestructionParticles(self)

        self.hitboxes = Hitboxes(self)

        # mouse state inits probably gonna have to make an input manager too
        self.mouse_state = {
            'left': False,
            'right': False,
            'left_hold': False,
            'right_hold': False,
            'left_release': False,
            'right_release': False,
            "scroll_up": False,
            "scroll_down": False
        }

        # input states init gon be moved to an input manager
        self.states = {
            "reload": False
        }

        # projectile images going to be put into an asset manager later
        self.projectile_images = load_dir('data/images/projectiles')

    def frame_start(self): # update function
        self.dt = time.time() - self.start_time
        self.start_time = time.time()
        self.mouse_pos = pygame.mouse.get_pos()

        # self.camera.update()
        self.vfx.update()
        self.particles.update()
        self.destruction_particles.update()
        self.hitboxes.update()

    def reset(self):
        self.scroll = []
        self.enemy_spawns = []
        self.spawn = (1, 0)
        self.edges = [10000000, -9999999, 9999999, -9999999]
        self.level_map = None
        self.input = [False, False, False]
        self.leaves = []
        # projectile inits probably gonna have to put it to an entity manager
        self.projectiles = []

        self.player = None

        # entity manager going to be moved
        self.entities = []
    
    def load_map(self, name):
        self.reset()
        self.level_map = tile_map.TileMap((TILE_SIZE, TILE_SIZE), self.display.get_size())
        self.level_map.load_map(f'data/maps/{name}.json')
        self.level_map.physical_check = lambda x : x in ['main_tileset']
        
        for entity in self.level_map.load_entities():
            entity_type = entity[2]['type'][1]
            if entity_type == 1:
                self.spawn = entity[2]['raw'][0]

        self.scroll = [self.spawn[1] - self.display.get_width() // 2, self.spawn[1] - self.display.get_height() // 2]

        for pos in self.level_map.tile_map:
            x = pos[0] * TILE_SIZE
            y = pos[1] * TILE_SIZE
            if x < self.edges[0]:
                self.edges[0] = x
            if x > self.edges[1]:
                self.edges[1] = x + TILE_SIZE
            if y < self.edges[2]:
                self.edges[2] = y
            if y > self.edges[3]:
                self.edges[3] = y + TILE_SIZE
        
        gd.player = Player(self, (gd.spawn[0], gd.spawn[1]), (27, 40), 'player')
        self.camera.set_tracked_entity(gd.player)

        self.entities.append(gd.player)
        self.entities.append(MetalHead(self, (gd.spawn[0], gd.spawn[1]), (15, 18), 'metalhead'))

# have to move player to an asset manager to get everything more clean and simple

class Player(Entity):
    def __init__(self, *args):
        super().__init__(*args)
        self.velocity = [0, 0]
        self.speed = 4
        self.accel = 0.3
        self.air_time = 0
        self.jump = 10
        self.dash = 0
        # self.wall_slide = False

        self.inventory = {}
        # self.inventory = {('active', 0): Weapon(gd, self, 'vector')}
        self.give_item(create_weapon(gd, self, 'vector'))
        self.give_item(create_weapon(gd, self, 'battle rifle'))
        self.give_item(create_weapon(gd, self, 'pistol'))
        self.give_item(create_weapon(gd, self, 'revolver'))
        self.give_item(create_weapon(gd, self, 'hatchet'))
        self.ammo = {
            'small': 108,
            'medium': 112
        }
        self.selected_slot = ('active', 0)

    @property
    def weapon(self):
        return self.inventory[self.selected_slot]

    def get_open_slot(self, slot_group):
        last = -1
        for item in self.inventory:
            if item[0] == slot_group:
                if item[1] > last + 1:
                    return last + 1
                if item[1] > last:
                    last = item[1]
        return last + 1

    def give_item(self, item, slot_group="active"):
        self.inventory[(slot_group, self.get_open_slot(slot_group))] = item

    def max_slot(self, slot_group):
        return max([slot[1] for slot in self.inventory if slot[0] == slot_group])

    def min_slot(self, slot_group):
        return min([slot[1] for slot in self.inventory if slot[0] == slot_group])

    def step_slot(self, current_slot, step_ammount):
        sorted_slots = sorted([slot[1] for slot in self.inventory if slot[0] == current_slot[0]])
        slot_index = sorted_slots.index(current_slot[1]) + step_ammount
        slot_index %= len(sorted_slots)

        return (current_slot[0], sorted_slots[slot_index])

    def get_items(self, slot_group):
        return [item[1] for item in sorted([(item[1], self.inventory[item]) for item in self.inventory if item[0] == slot_group])]

    def update(self, gd):
        super().update(gd.dt)
        # print(self.velocity) # change is using maths
        if not self.dash:
            self.velocity[0] = normalize(self.velocity[0], 0.03 * gd.dt)
        else:
            self.velocity[0] = normalize(self.velocity[0], 0.03 * gd.dt)
            self.velocity[1] = normalize(self.velocity[1], 0.03 * gd.dt)

        rects = [t[1] for t in gd.level_map.get_nearby_rects(self.center)]
        self.velocity[1] = min(4, self.velocity[1] + 0.25)

        if (abs(self.velocity[0]) < self.speed) or (not(gd.input[0] or gd.input[1])):
            if abs(self.velocity[0]) <= self.speed:
                self.velocity[0] *= 0.9
            else:
                self.velocity[0] *= 0.97
        if abs(self.velocity[0]) < 0.2:
            self.velocity[0] = 0

        if gd.input[0]: # left
            if self.velocity[0] > -self.speed:
                self.velocity[0] -= self.accel
                self.velocity[0] = max(-self.speed, self.velocity[0])
        if gd.input[1]: # right
            if self.velocity[0] < self.speed:
                self.velocity[0] += self.accel
                self.velocity[0] = min(self.speed, self.velocity[0])
        if gd.input[2]: # jump
            if self.jump >= 0:
                if self.jump == 4:
                    self.velocity[0] *= 1.2
                self.jump -= 1
                self.velocity[1] = -3.5
                self.air_time = 6
                if self.jump <= 0:
                    gd.input[2] = False
        elif self.jump < 5:
            self.jump = 0

        self.air_time += gd.dt
        collisions = self.move(self.velocity, rects)
        if collisions['top']:
            self.jump = 0
        if collisions['top'] or collisions['bottom']:
            self.velocity[1] = 1
            self.air_time = 0

        if collisions['right'] or collisions['left']:
            self.velocity[0] = 0

        # weapon stuff
        angle = math.atan2(gd.mouse_pos[1] - self.center[1] + gd.camera.render_offset[1], gd.mouse_pos[0] - self.center[0] + gd.camera.render_offset[0])
        self.weapon.rotation = math.degrees(angle)

        if gd.states['reload']:           
            self.weapon.reload()
        
        for control in self.weapon.controls:
            if gd.mouse_state[control]:
                self.weapon.attack()
                # add_freeze(0.2, 0.2) # move it its just for testing !

        # dash
        self.dash -= gd.dt
        self.dash = max(0, self.dash)

        if self.dash:
            img, img_clone = self.img.copy(), self.img.copy()
            img.set_alpha(60)
            img_clone.set_alpha(random.randint(70, 90))
            gd.vfx.spawn_group('arrow_impact_sparks', self.center.copy(), angle, layer="front")
            gd.vfx.spawn_group('dash_sparks_2', self.center.copy(), angle, color=(255, 0, 0), layer="front")
            gd.destruction_particles.add_particle(img, self.center.copy(), [0, 0, 0], duration=0.1, gravity=False)
            if self.dash > 0.43:
                gd.destruction_particles.add_particle(img_clone, self.center.copy(), [random.random() * 3 * angle, random.random() * random.randint(-3, 3),random.random() * 3], duration=random.randint(1,5), gravity=False)

        if gd.mouse_state['right']:
            self.velocity[0] = math.cos(angle) * 10
            self.velocity[1] = math.sin(angle) * 10
            self.dash = 0.5
            for i in range(random.randint(15, 30)):
                gd.vfx.spawn_group('previous_dash_sparks', self.center.copy(), angle, layer="front")

        # inventory
        if gd.mouse_state['scroll_up']:
            self.selected_slot = self.step_slot(self.selected_slot, 1)

        if gd.mouse_state['scroll_down']:
            self.selected_slot = self.step_slot(self.selected_slot, -1)

        if self.air_time > 5:
            self.set_action('jump')
        else:
            self.jump = 10
            if gd.input[0] or gd.input[1]:
                self.set_action('run')
            else:
                self.set_action('idle')

        if (self.weapon.rotation % 360 < 270) and (self.weapon.rotation % 360 > 90):
            self.flip[0] = True
        else:
            self.flip[0] = False

    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset)
        self.weapon.render(surf, (self.center[0] - offset[0], self.center[1] - offset[1]))

pygame.init()
pygame.display.set_caption('Herugōsuto')

screen = pygame.display.set_mode((1920, 1080), 0, 32)

TILE_SIZE = 24

clock = pygame.time.Clock()

animation_manager = AnimationManager()
font_white = Font('data/fonts/small_font.png', (255, 255, 255))

spritesheets, spritesheets_data = spritesheet_loader.load_spritesheets('data/images/spritesheets/')

foliage_animations = [AnimatedFoliage(load_img('data/images/foliage/' + str(i) + '.png', colorkey=(0, 0, 0)), [[60, 3, 12], [104, 10, 0], [137, 9, 9], [156, 24, 24], [187, 0, 0], [224, 0, 0], [234, 97, 5]], motion_scale=0.2) for i in range(1)]
# load_particle_images('data/images/particles')


# light masking might be put into an asset manager
light_mask_base = load_img('data/images/lights/light.png')
light_mask_base_blue = light_mask_base.copy()
light_mask_base_blue.fill((49, 123, 255))
light_mask_base_blue.blit(light_mask_base, (0, 0), special_flags=BLEND_RGBA_MULT)
light_mask_full = pygame.transform.scale(light_mask_base, (400, 300))
light_mask_full.blit(light_mask_full, (0, 0), special_flags=BLEND_RGBA_ADD)
light_masks = []
light_masks_blue = []
for radius in range(1, 850):
    light_masks.append(pygame.transform.scale(light_mask_base, (radius, radius)))
for radius in range(1, 50):
    light_masks_blue.append(pygame.transform.scale(light_mask_base_blue, (radius, radius)))

# def glow(surf, host, pos, radius):
#     timing_offset = (hash(host) / 1000) % 1
#     glow_width = int(math.sin(global_time / 50 + timing_offset * math.pi * 2) * radius * 0.3 + radius * 0.7)
#     glow_img = light_masks[glow_width - 1]
#     surf.blit(glow_img, (pos[0] - glow_width // 2, pos[1] - glow_width // 2), special_flags=BLEND_RGBA_ADD)

def glow(surf, host, pos, radius, blue=False):
    if host:
        timing_offset = (hash(host) / 1000) % 1
    else:
        timing_offset = 0
    glow_width = int(math.sin(global_time / 30 + timing_offset * math.pi * 2) * radius * 0.15 + radius * 0.85)
    if not blue:
        glow_img = light_masks[glow_width - 1]
    else:
        glow_img = light_masks_blue[glow_width - 1]
    surf.blit(glow_img, (pos[0] - glow_width // 2, pos[1] - glow_width // 2), special_flags=BLEND_RGBA_ADD)

grass_manager = GrassManager('data/images/grass', tile_size=TILE_SIZE)

# fly data, might be put into its own file and rendered with the asset manager later
class Fly:
    def __init__(self, data):
        self.data = data

soul_flies = []
for i in range(30):
    soul_flies.append(Fly([[random.random() * 300, random.random() * 200], random.random() * math.pi * 2, 0, random.random() * 0.5 + 0.2]))

gd = GameData()
gd.load_map('save')
gd.level_map.load_grass(grass_manager)

global_time = 0

# background prob gon be moved to another file
background_offset = 0
bg_bubbles = []
bg_bubble_particles = []

bg_particles = []
height = 0

SQUARE_CACHE = {}

class Square:
    def __init__(self, base_location, location, size, speed):
        self.rotation = random.random() * math.pi * 2
        self.rot_speed = (random.random() - 0.5) * 4
        self.width = random.randint(4, 8)

        self.location = list(location)
        self.base_location = list(base_location)
        self.size = size
        self.speed = speed

        self.parallax_rate = random.random() * 0.045
        self.location[0] *= self.parallax_rate
        self.location[1] *= self.parallax_rate

    def update(self, dt):
        self.location[1] -= self.speed * dt
        self.size -= dt
        self.rotation += self.rot_speed * dt
        if self.size < 0:
            return False
        else:
            return True

    def render(self, surf, offset=(0, 0)):

        size = int(self.size * 2)
        rot = int(math.degrees(self.rotation) / 15) * 15
        img_id = (size, rot)

        if img_id not in SQUARE_CACHE:
            square_surf = pygame.Surface((int(size * 1.2), int(size * 1.2)))
            square_surf.set_colorkey((0, 0, 0))
            pygame.draw.rect(square_surf, (29, 0, 38), pygame.Rect(size * 0.1, size * 0.1, size, size), width = self.width)
                
            square_surf = pygame.transform.rotate(square_surf, rot)
            SQUARE_CACHE[img_id] = square_surf
        else:
            square_surf = SQUARE_CACHE[img_id]

        surf.blit(square_surf, (self.location[0] - square_surf.get_width() // 2 - offset[0] * self.parallax_rate + self.base_location[0], self.location[1] - square_surf.get_height() // 2 - offset[1] * self.parallax_rate + self.base_location[1]))

class Background:
    def __init__(self):
        self.speed = 20

        self.squares = []
        self.spawn_timer = 0

    def update(self, scroll):
        if not len(self.squares):
            for i in range(20):
                self.squares.append(Square([random.random() * gd.display.get_width(), random.random() * gd.display.get_height()], scroll, random.randint(5, 20), random.randint(15, 60)))

        self.spawn_timer += 0.06
        while self.spawn_timer > 0.2:
            self.spawn_timer -= 0.2
            self.squares.append(Square([random.random() * gd.display.get_width(), random.random() * gd.display.get_height()], scroll, random.randint(5, 20), random.randint(15, 60)))

        for i, square in itr(self.squares):
            alive = square.update(gd.dt)
            if not alive:
                self.squares.pop(i)

    def render(self, surf, scroll):
        for square in self.squares:
            square.render(surf, offset=scroll)

def generate_terrain_particles(surf, terrain_particle_queue, particles, scroll, tile_map, particle_img, global_time):
    display_r = pygame.Rect(0, 0, *surf.get_size())
    
    for base_pos, movement in terrain_particle_queue:
        for i in range(random.randint(1, 4)):
            pos = [base_pos[0] + random.random() * 4 - 2, base_pos[1] + random.random() * 3 - 1]
            display_pos = (int(pos[0] - scroll[0]), int(pos[1] - scroll[1]))
            if display_r.collidepoint(display_pos):
                color = tuple(surf.get_at(display_pos))
                particles.add_particles('foreground', pos, 'p_terrain', [(random.random() * 20 - 10 + (movement[0] * (dt))) * (dt), ((40 - random.random() * 60) * (dt))], random.uniform(0.02, 0.06), random.choice([4, 5, 5]), tile_map, particle_img, global_time, custom_color=color)

background = Background()

while True:
    gd.frame_start()
    global_time += 1

    gd.display.fill((13, 0, 72))
    light_surf = gd.display.copy()
    light_surf.fill((0, 12, 37))

    gd.scroll[0] += (gd.player.center[0] - gd.display.get_width() // 2 - gd.scroll[0]) / 18
    gd.scroll[1] += (gd.player.center[1] - gd.display.get_height() // 2 - gd.scroll[1]) / 18

    # if gd.scroll[0] < gd.edges[0]:
    #     gd.scroll[0] = gd.edges[0]
    # if gd.scroll[0] > gd.edges[1] - gd.display.get_width():
    #     gd.scroll[0] = gd.edges[1] - gd.display.get_width()
    # if gd.scroll[1] < gd.edges[2]:
    #     gd.scroll[1] = gd.edges[2]
    # if gd.scroll[1] > gd.edges[3] - gd.display.get_height():
    #     gd.scroll[1] = gd.edges[3] - gd.display.get_height()

    if random.random() < 0.1:
        if random.random() > 0.25:
            bg_bubbles.append([[random.random() * 600, 400], random.random() * 2.5 + 0.25, random.random() * 18 + 1, random.random() - 0.5])
        else:
            bg_bubbles.append([[random.random() * 600, 0], random.random() * -2.5 - 0.25, random.random() * 18 + 1, random.random() - 0.5])
    for i, bubble in itr(bg_bubbles):
        bg_bubble_particles.append([((bubble[0][0] + gd.scroll[0] * bubble[3]) % 600, bubble[0][1]), bubble[2]])
        bubble[0][1] -= bubble[1]
        if (bubble[0][1] < 0) or (bubble[0][1] > 400):
            bg_bubbles.pop(i)

    for i, p in itr(bg_bubble_particles):
        pygame.draw.circle(gd.display, (0, 0, 0), p[0], int(p[1]))
        p[1] -= 0.3
        if p[1] <= 0:
            bg_bubble_particles.pop(i)

    parallax = random.random()
    for i in range(1):
        bg_particles.append([[random.random() * gd.display.get_width(), gd.display.get_height() - height * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice([(0, 0, 0), (14, 0, 57)])])

    for i, p in sorted(enumerate(bg_particles), reverse=True):
        size = p[2]
        # if p[-1] != (0, 0, 0):
        #     size = size * 5 + 4
        p[2] -= 0.01
        p[0][1] -= p[3]
        if size < 1:
            gd.display.set_at((int(p[0][0]), int(p[0][1] + height * p[1])), (0, 0, 0))
        else:
            if p[-1] != (0, 0, 0):
                pygame.draw.circle(gd.display, p[-1], p[0], int(size), 4)
            else:
                pygame.draw.circle(gd.display, p[-1], p[0], int(size))
        if size < 0:
            bg_particles.pop(i)

    background.update(gd.scroll)
    background.render(gd.display, gd.scroll)

    background_offset = (background_offset + 0.25) % 30
    for i in range(18):
        pygame.draw.line(gd.display, (31, 0, 40), (-10, int(i * 30 + background_offset - 20)), (gd.display.get_width() + 20, int(i * 30 - 110 + background_offset)), 15)

    gd.player.update(gd)
    gd.camera.update()

    # vfx stuff prob gon move
    gd.vfx.render_back(gd.display, gd.scroll)

    entities_rendered = False
    render_list = gd.level_map.get_visible(gd.scroll)
    for layer in render_list:
        layer_id = layer[0]

        if not entities_rendered:
            if layer_id >= -4:
                gd.player.render(gd.display, gd.scroll)

        for tile in layer[1]:
            if tile[1][0] == "foliage":
                seed = int(tile[0][1] * tile[0][0] + (tile[0][0] + 10000000) ** 1.2)
                foliage_animations[tile[1][1]].render(gd.display, (tile[0][0] - gd.scroll[0], tile[0][1] - gd.scroll[1]), m_clock=global_time / 100, seed=seed)
                chance = 0.02
                if tile[1][1] == 2:
                    chance = 0.003
                if random.random() < chance:
                    pos = foliage_animations[tile[1][1]].find_leaf_point() 
                    gd.leaves.append(Particle(tile[0][0] + pos[0], tile[0][1] + pos[1], 'grass', [random.random() * 10 + 10, 8 + random.random() * 4], 0.7 + random.random() * 0.6, random.random() * 2, custom_color=random.choice([[60, 3, 12], [104, 10, 0], [137, 9, 9], [156, 24, 24], [187, 0, 0], [224, 0, 0], [234, 97, 5]])))
            else:
                offset = [0, 0]
                if tile[1][0] in spritesheets_data:
                    tile_id = str(tile[1][1]) + ';' + str(tile[1][2])
                    if tile_id in spritesheets_data[tile[1][0]]:
                        if 'tile_offset' in spritesheets_data[tile[1][0]][tile_id]:
                            offset = spritesheets_data[tile[1][0]][tile_id]['tile_offset']
                img = spritesheet_loader.get_img(spritesheets, tile[1])
                gd.display.blit(img, (tile[0][0] - gd.scroll[0] + offset[0], tile[0][1] - gd.scroll[1] + offset[1]))
    
    # particle stuff prob gon be moved
    # if random.random() < 0.1:
        # gd.particles.add_particle('foreground', gd.player.pos, 'shells', [0, 0], 0.5, 0, custom_color=(246, 255, 0), physics=gd.level_map)
    gd.particles.render('foreground', gd.display, gd.scroll)
    gd.destruction_particles.render(gd.display, gd.scroll)

    # vfx stuff prob gon be moved
    gd.vfx.render_front(gd.display, gd.scroll)

    grass_manager.update_render(gd.display, gd.dt, offset=gd.scroll.copy(), rot_function=lambda x, y: int((math.sin(x / 100 + global_time / 40) + 0.4) * 30) / 10)
    grass_manager.apply_force((gd.player.center[0], gd.player.center[1]), 10, 20)

    # entity manager stuff gon be moved
    for entity in gd.entities:
        if entity != gd.player:
            entity.update(gd.dt)
            entity.render(gd.display, gd.scroll)

    # particles
    for particle in gd.leaves.copy():
        alive = particle.update(gd.dt)
        shift = math.sin(particle.x / 20 + global_time / 40) * 16
        shift *= min(1, particle.time_alive)
        particle.draw(gd.display, (gd.scroll[0] + shift, gd.scroll[1]))
        if not alive:
            gd.leaves.remove(particle)

    for fly_obj in soul_flies:
        fly = fly_obj.data
        fly[0][0] += math.cos(fly[1]) * fly[3]
        fly[0][1] += math.sin(fly[1]) * fly[3]
        fly[1] += fly[2]
        if random.random() < 0.01:
            # fly[2] += random.random() * 0.01
            fly[2] = random.random() * 0.2 - 0.1
        render_pos = (int(fly[0][0] - gd.scroll[0] * 1.5) % 600, int(fly[0][1] - gd.scroll[1] * 1.5) % 400)
        gd.display.set_at(render_pos, (109, 202, 232))
        glow(light_surf, fly_obj, render_pos, 5, blue=True)
        glow(light_surf, fly_obj, render_pos, 18, blue=True)

    # projectile stuff
    for i, projectile in itr(gd.projectiles):
        alive = projectile.update(gd.dt)
        if not alive:
            gd.projectiles.pop(i)
        projectile.render(gd.display, gd.scroll)

    # hud lighting? goes to shader manager later

    # lighting
    for entity in gd.entities:
        if entity != gd.player:
            glow(light_surf, entity, (entity.center[0] - gd.scroll[0], entity.center[1] - gd.scroll[1]), 120)
    glow(light_surf, gd.player, (gd.player.center[0] - gd.scroll[0], gd.player.center[1] - gd.scroll[1]), 480)
    gd.display.blit(light_surf, (0, 0), special_flags=BLEND_RGBA_MULT)

    # mouse state resets, should be a soft reset in an input manager
    gd.mouse_state['left'] = False
    gd.mouse_state['right'] = False
    gd.mouse_state['left_release'] = False
    gd.mouse_state['right_release'] = False
    gd.mouse_state['scroll_up'] = False
    gd.mouse_state['scroll_down'] = False

    # input states in a soft reset in an input manager
    gd.states['reload'] = False

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.quit()
            if event.key in [K_LEFT, K_a]:
                gd.input[0] = True
            if event.key in [K_RIGHT, K_d]:
                gd.input[1] = True
            if event.key in [K_UP, K_SPACE, K_w]:
                gd.input[2] = True
            if event.key in [K_r]:
                gd.states['reload'] = True
        
        if event.type == KEYUP:
            if event.key in [K_LEFT, K_a]:
                gd.input[0] = False
            if event.key in [K_RIGHT, K_d]:
                gd.input[1] = False
            if event.key in [K_UP, K_SPACE, K_w]:
                gd.input[2] = False

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                gd.mouse_state['left'] = True
                gd.mouse_state['left_hold'] = True
            if event.button == 3:
                gd.mouse_state['right'] = True
                gd.mouse_state['right_hold'] = True
            if event.button == 4:
                gd.mouse_state['scroll_up'] = True
            if event.button == 5:
                gd.mouse_state['scroll_down'] = True
        if event.type == MOUSEBUTTONUP:
            if event.button == 1:
                gd.mouse_state['left_release'] = True
                gd.mouse_state['left_hold'] = False
            if event.button == 3:
                gd.mouse_state['right_release'] = True
                gd.mouse_state['right_hold'] = False

    # freeze frames -- move and change its just for testing !
    delete_list = []

    if freeze_frame != {}:
        slowest_freeze = min(list(freeze_frame))
        if freeze_frame[slowest_freeze] > gd.dt:
            gd.dt *= slowest_freeze * 5
        else:
            gd.dt -= freeze_frame[slowest_freeze] * (1 - slowest_freeze)
    
    for freeze_amount in freeze_frame:
        if freeze_frame[freeze_amount] > gd.dt:
            freeze_frame[freeze_amount] -= gd.dt
        else:
            freeze_frame[freeze_amount] = 0
            delete_list.append(freeze_amount)

    for freeze in delete_list:
        del freeze_frame[freeze]

    # ui elements
    gd.display.blit(gd.misc['cursor'], (gd.mouse_pos[0] - gd.window_offset[0] - gd.misc['cursor'].get_width() // 2, gd.mouse_pos[1] - gd.window_offset[1] - gd.misc['cursor'].get_height() // 2))
    # font_white.render('fps:' + str(int(clock.get_fps())), gd.display, (2, 10))
    # font_white.render(str(gd.player.weapon.ammo) + '/' + str(gd.player.ammo[gd.player.weapon.ammo_type]), gd.display, (2, 2))
    font_white.render(str(gd.player.weapon.ammo) + '/', gd.display, (31, 5))
    font_white.render(str(gd.player.ammo[gd.player.weapon.ammo_type]), gd.display, (34, 13))

    # temporary hud
    gd.display.blit(gd.misc['health'], (-8, 4))
    # gd.display.blit(gd.misc[gd.player.weapon.type], (8, 18))
    gd.display.blit(gd.misc['skills'], (3, 334))

    screen.blit(pygame.transform.scale(gd.display, (1920, 1080)), (0, 0))
    pygame.display.update()
    clock.tick(60)
    # print(clock.get_fps())
