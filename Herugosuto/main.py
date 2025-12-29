import pygame, sys, os, random, math, json, time
import data.engine as e
import data.particles_advanced as p
import data.destruction_particles as dp
import data.outline as o
import data.minimap as mp
import data.tile_map as tile_map
import data.spritesheet_loader as spritesheet_loader
import data.particles as particles_m

from data.grass import GrassManager
from data.foliage import AnimatedFoliage
from data.particles import Particle, load_particle_images
from data.particles_advanced import ParticleManager
from data.grass import *
from data.core_funcs import *
from data.bezier import generate_line_chain_vfx
from data.item_drop import ItemDrop
from data.tooltips import *
from data.entity import Entity
from data.anim_loader import AnimationManager

clock = pygame.time.Clock()

from pygame.locals import *
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init() # initiates pygame
pygame.mixer.set_num_channels(64)

pygame.display.set_caption('Herugōsuto')
pygame.mouse.set_visible(False)

WINDOW_SIZE = (1440, 810)

screen = pygame.display.set_mode(WINDOW_SIZE,0,32) # initiate the window

display = pygame.Surface((480, 270)) # used as the surface for rendering, which is scaled
window_offset = [240, 135]
global_time = 0
tutorial_x = -100

animation_manager = AnimationManager()

bar_height = 100
win = 0
game_speed = 1

# variables
moving_right = False
moving_left = False
vertical_momentum = 0
air_timer = 0
player_direction = 1

TILE_SIZE = 16

background_offset = 0
bg_bubbles = []
bg_bubble_particles = []

bg_particles = []
height = 0
screen_shake = 0

load_particle_images('data/images/particles')

with open("data/projectiles.json", "r") as f:
    gun_config = json.load(f)

with open("data/weapons.json", "r") as f:
    gun_var_config = json.load(f)

with open("data/entities.json", "r") as f:
    entities_config = json.load(f)

with open("data/hitboxes.json", "r") as f:
    hitboxes_config = json.load(f)

true_scroll = [-8865, -3000]

# functions
dt = 1 / 60
frame_start = time.time()

freeze_frame = {}

def add_freeze(rate, duration):
    time.sleep(0.05)
    freeze_frame[rate] = duration

def load_snd(name):
    return pygame.mixer.Sound('data/sfx/' + name + '.wav')

def clip(surf,x,y,x_size,y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x,y,x_size,y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()

def advance(pos, angle, amt):
    pos[0] += math.cos(angle) * amt
    pos[1] += math.sin(angle) * amt
    return pos

def itr(l):
    return sorted(enumerate(l), reverse=True)

def center(pos, size, centered):
    if centered:
        return pos.copy()
    else:
        return [pos[0] + size[0] // 2, pos[1] + size[1] // 2]

def render_offset(true_pos, window_offset):
    return [true_pos[0] - window_offset[0], true_pos[1] - window_offset[1]]

def rdm(scale, offset):
    return random.random() * scale + offset

def point_surf(point_list):
    x_positions = [v[0] for v in point_list]
    y_positions = [v[1] for v in point_list]
    min_x = min(x_positions)
    min_y = min(y_positions)
    size_x = max(x_positions) - min_x + 1
    size_y = max(y_positions) - min_y + 1
    new_surf = pygame.Surface((int(size_x), int(size_y)))
    new_surf.set_colorkey((0, 0, 0))
    new_points = [[v[0] - min_x, v[1] - min_y] for v in point_list]
    return new_surf, new_points, [min_x, min_y]

def load_img(path, colorkey=None, scale=1):
    img = pygame.image.load(path).convert()
    img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
    if colorkey:
        img.set_colorkey(colorkey)
    return img

def load_dir(path):
    image_dir = {}
    for file in os.listdir(path):
        image_dir[file.split('.')[0]] = load_img(path + '/' + file, (0, 0, 0))
    return image_dir

def load_dir_list(path):
    image_ids = sorted([(int(file.split('.')[0].split('_')[-1]), file) for file in os.listdir(path)])
    images = [load_img(path + '/' + img[1], (0, 0, 0)) for img in image_ids]
    return images

def normalize(num, amt):
    if num > amt:
        num -= amt
    elif num < -amt:
        num += amt
    else:
        num = 0
    return num

def get_dis(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def to_cart(angle, dis):
    return [math.cos(angle) * dis, math.sin(angle) * dis]

def to_polar(vector):
    return [math.atan2(*(vector[::-1])), get_dis([0, 0], vector)]

def physical_rect_filter(tiles):
    valid = []
    for tile in tiles:
        for tile_type in tile[0]:
            if tile_type[0] in ["main_tileset"]:
                valid.append(tile[1])
                break
    return valid

# player functions

class StyleMeter:
    def __init__(self):
        self.current_style = 0
        self.target_style = 0
        self.maximum_style = 1000
        self.style_meter_length = 100
        self.style_ratio = self.maximum_style / self.style_meter_length
        self.style_change_speed = 5
    
    def remove_style(self, amount):
        if self.target_style > 0:            
            self.target_style -= amount		
        if self.target_style < 0:            
            self.target_style = 0

    def add_style(self, amount):
        if self.target_style < self.maximum_style:            
            self.target_style += amount		
        if self.target_style > self.maximum_style:            
            self.target_style = self.maximum_style

    def update(self, surf):
        self.style_bar(surf)
    
    def style_bar(self, surf):
        transition_width = 0
        transition_color = (255,0,0)
        background_colour = (157, 142, 181, 128)

        if self.current_style < self.target_style:
            self.current_style += self.style_change_speed
            transition_width = int((self.target_style - self.current_style) / self.style_ratio)
            transition_color = (245, 2, 2)

        if self.current_style > self.target_style:
            self.current_style -= self.style_change_speed 
            transition_width = int((self.target_style - self.current_style) / self.style_ratio)
            transition_color = (255, 197, 0)

        style_bar_width = int(self.current_style / self.style_ratio)
        style_bar = pygame.Rect(surf.get_width() - (self.style_meter_length + 11), 100, style_bar_width, 10)
        transition_bar = pygame.Rect(style_bar.right, 101, transition_width, 10)
        
        # pygame.draw.rect(surf, background_colour, ((surf.get_width() - (self.style_meter_length + 16)), 102, self.style_meter_length + 10, 80))
        background_surface = pygame.Surface((self.style_meter_length + 10, 80))
        background_surface.set_alpha(89)
        background_surface.fill(background_colour)
        surf.blit(background_surface, ((surf.get_width() - (self.style_meter_length + 16)), 102))
        pygame.draw.rect(surf,transition_color,transition_bar)	
        pygame.draw.rect(surf,(255, 255, 255),style_bar)
        pygame.draw.rect(surf,(255, 255, 255),(surf.get_width() - (self.style_meter_length + 11), 100, self.style_meter_length, 10), 1)

style_meter = StyleMeter()

def get_open_slot(inventory, slot_group):
    last = -1
    for item in inventory:
        if item[0] == slot_group:
            if item[1] > last + 1:
                return last + 1
            if item[1] > last:
                last = item[1]
    return last + 1

def player_give_item(inventory, item, slot_group='active'):
    inventory[(slot_group, get_open_slot(inventory, slot_group))] = item

def max_slot(inventory, slot_group):
    return max([slot[1] for slot in inventory if slot[0] == slot_group])

def min_slot(inventory, slot_group):
    return min([slot[1] for slot in inventory if slot[0] == slot_group])

def step_slot(inventory, current_slot, step_ammount):
    sorted_slots = sorted([slot[1] for slot in inventory if slot[0] == current_slot[0]])
    slot_index = sorted_slots.index(current_slot[1]) + step_ammount
    slot_index %= len(sorted_slots)

    return (current_slot[0], sorted_slots[slot_index])

def player_weapon(inventory, selected_slot):
    return inventory[selected_slot]

def get_items(inventory, slot_group):
    return [item[1] for item in sorted([(item[1], inventory[item]) for item in inventory if item[0] == slot_group])]

class Font():
    def __init__(self, path):
        self.spacing = 1
        self.character_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':','+','\'','!','?','0','1','2','3','4','5','6','7','8','9','(',')','/','_','=','\\','[',']','*','"','<','>',';']
        font_img = pygame.image.load(path).convert()
        font_img.set_colorkey((0, 0, 0))
        current_char_width = 0
        self.characters = {}
        self.letter_spacing = []
        character_count = 0
        last_x = 0
        for x in range(font_img.get_width()):
            c = font_img.get_at((x, 0))
            if c[0] == 127:
                char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
                self.characters[self.character_order[character_count]] = char_img.copy()
                character_count += 1
                current_char_width = 0
                self.letter_spacing.append(x - last_x)
                last_x = x + 1
            else:
                current_char_width += 1
        self.space_width = self.characters['A'].get_width()

    def width(self, text):
        text_width = 0
        for char in text:
            if char == ' ':
                text_width += self.space_width + self.spacing
            else:
                text_width += self.letter_spacing[self.character_order.index(char)] + self.spacing
        return text_width

    def render(self, surf, text, loc):
        x_offset = 0
        for char in text:
            if char != ' ':
                surf.blit(self.characters[char], (loc[0] + x_offset, loc[1]))
                x_offset += self.characters[char].get_width() + self.spacing
            else:
                x_offset += self.space_width + self.spacing

small_font = Font("data/fonts/small_font.png")
large_font = Font("data/fonts/large_font.png")
dark_font = Font("data/fonts/black_font.png")

class PlainLine:
    def __init__(self, pos1, pos2, decay_rate, width=1, color=(255, 255, 255, 255)):
        self.pos1 = pos1
        self.pos2 = pos2
        self.decay_rate = decay_rate
        self.color = color
        self.width = width

    def update(self):
        self.color = (self.color[0], self.color[1], self.color[2], max(0, self.color[3] - self.decay_rate))
        return bool(self.color[3])

    def render(self, surf, offset=(0, 0)):
        new_surf, new_points, base_offset = point_surf([[self.pos1[0] - offset[0], self.pos1[1] - offset[1]], [self.pos2[0] - offset[0], self.pos2[1] - offset[1]]])
        pygame.draw.line(new_surf, self.color, new_points[0], new_points[1], self.width)
        new_surf.set_alpha(self.color[3])
        surf.blit(new_surf, base_offset)

class CurvedSpark:
    def __init__(self, pos, angle, curve, speed, scale, decay_rate, fatness=1, color=(255, 255, 255)):
        self.pos = list(pos)
        self.angle = angle
        self.curve = curve
        self.scale = scale
        self.color = color
        self.speed = speed
        self.fatness = fatness
        self.decay_rate = decay_rate

    def update(self):
        self.pos[0] += math.cos(self.angle) * self.speed
        self.pos[1] += math.sin(self.angle) * self.speed
        self.angle += self.curve * self.speed
        self.speed = max(0, self.speed - self.decay_rate)

        return bool(self.speed)

    def render(self, surf, offset=(0, 0)):
        if self.speed:
            iterations = 10
            position = self.pos.copy()
            temp_angle = self.angle
            points = []
            for i in range(iterations // 2):
                temp_angle -= self.curve * self.speed * self.scale / iterations
                position[0] -= math.cos(temp_angle) * self.speed * self.scale / iterations
                position[1] -= math.sin(temp_angle) * self.speed * self.scale / iterations
            for i in range(iterations + 1):
                progress = i / iterations

                dif = ((0.5 - abs(0.5 - progress)) * 2) ** (1 / 2.5)
                points.append([position[0] + math.cos(temp_angle + math.pi / 2) * self.scale * dif * 0.05 * self.fatness * self.speed, position[1] + math.sin(temp_angle + math.pi / 2) * self.scale * dif * 0.05 * self.fatness * self.speed])
                points = [[position[0] + math.cos(temp_angle - math.pi / 2) * self.scale * dif * 0.05 * self.fatness * self.speed, position[1] + math.sin(temp_angle - math.pi / 2) * self.scale * dif * 0.05 * self.fatness * self.speed]] + points

                position[0] += math.cos(temp_angle) * self.speed * self.scale / iterations
                position[1] += math.sin(temp_angle) * self.speed * self.scale / iterations
                temp_angle += self.curve * self.speed * self.scale / iterations

            for p in points:
                 p[0] -= offset[0]
                 p[1] -= offset[1]

            new_surf, new_points, base_offset = point_surf(points)
            pygame.draw.polygon(surf, self.color, points)
            if len(self.color) == 4:
                new_surf.set_alpha(self.color[3])
                surf.blit(new_surf, base_offset)
                
class Arc():
    def __init__(self, pos, radius, spacing, start_angle, speed, curve_rate, scale, start=0, end=1, duration=30, color=(255, 255, 255), fade=0.3, arc_stretch=0, width_decay=50, motion=0 , decay=['up', 60], angle_width=0.2):
        self.start_angle = start_angle
        self.speed = speed
        self.curve_rate = curve_rate
        self.scale = scale
        self.time = 0
        self.spacing = spacing
        self.radius = radius
        self.angle_width = angle_width
        self.width = 0.05
        self.start = start
        self.end = end
        self.duration = duration
        self.color = color
        self.fade = fade
        self.pos = list(pos)
        self.arc_stretch = arc_stretch
        self.width_decay = width_decay
        self.motion = motion
        self.decay = decay
        self.alive = True

    def get_angle_point(self, base_point, t, curve_rate):
        p = advance(base_point.copy(), self.start_angle + (0.5 * t) * math.pi * 4 * self.angle_width, self.radius)
        advance(p, self.start_angle, (0.5 ** 2 - abs(0.5 - t) ** 2) * self.radius* curve_rate)
        if self.arc_stretch != 0:
            advance(p, self.start_angle + math.pi / 2, (0.5 - t) * self.arc_stretch * self.scale)
        return p

    def calculate_points(self, start, end, curve_rate):
        base_point = advance([0, 0], self.start_angle, self.spacing)
        point_count = 20
        arc_points = [self.get_angle_point(base_point, start + (i / point_count) * (end - start), curve_rate) for i in range(point_count + 1)]
        arc_points = [[p[0] * self.scale, p[1] * self.scale] for p in arc_points]
        return arc_points

    def update(self):
        self.time += self.speed * (dt)
        if self.decay[0] == 'up':
            self.start -= self.start / 20 * (dt) * self.decay[1]
        elif self.decay[0] == 'down':
            self.end += (1 - self.end) / 20 * (dt) * self.decay[1]
        self.width += (1 - self.width) / 4 * (dt) * self.width_decay
        self.spacing += self.motion * (dt)
        if self.time > self.duration:
            self.alive = False
            return False
        return True

    def create_mask(self):
        start = self.start
        end = self.end
        points = self.calculate_points(start, end, self.curve_rate + self.time / 12) + self.calculate_points(start, end, (self.curve_rate + self.time / 12) * 0.5)[::-1]
        points = [[p[0] + self.pos[0], p[1] + self.pos[1]] for p in points]
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        min_x = min(points_x)
        min_y = min(points_y)
        mask_surf = pygame.Surface((max(points_x) - min_x + 1, max(points_y) - min_y + 1))
        points = [[p[0] - min_x, p[1] - min_y] for p in points]
        pygame.draw.polygon(mask_surf, (255, 255, 255), points)
        mask_surf.set_colorkey((0, 0, 0))
        return pygame.mask.from_surface(mask_surf), (min_x, min_y)

    def render(self, surf, offset=(0, 0)):
        if self.time > 0:
            start = self.start
            end = self.end
            points = self.calculate_points(start, end, self.curve_rate + self.time / 12) + self.calculate_points(start, end, (self.curve_rate + self.time / 12) * 0.5)[::-1]
            points = [[p[0] - offset[0] + self.pos[0], p[1] - offset[1] + self.pos[1]] for p in points]
            c = [int(self.color[i] - self.color[i] * self.fade * self.time / self.duration) for i in range(3)]
            pygame.draw.polygon(surf, c, points)

class Slice:
    def __init__(self, pos, angle, length, width, decay_rate, speed=0):
        self.angle = angle
        self.length = length
        self.orig_length = length
        self.width = width
        self.decay_rate = decay_rate
        self.time_left = 1
        self.pos = list(pos)
        self.speed = speed

    def update(self):
        self.time_left -= self.decay_rate * (dt)
        self.length = self.time_left * self.length
        if self.time_left < 0:
            return False
        else:
            return True

    def render(self, surf, offset=(0, 0)):
        pos = [self.pos[0] - offset[0], self.pos[1] - offset[1]]
        advance(pos, self.angle, (self.orig_length - self.length) * self.speed)
        points = [
            advance(pos.copy(), self.angle, self.length),
            advance(pos.copy(), self.angle + math.pi / 2, self.width * (self.length / self.orig_length)),
            advance(pos.copy(), self.angle + math.pi, self.length),
            advance(pos.copy(), self.angle + math.pi * 3 / 2, self.width * (self.length / self.orig_length))
        ]
        pygame.draw.polygon(surf, (255, 255, 255), points)

# VFX stuff

VFX_TYPES = {
    'curved_spark': CurvedSpark,
    'plain_line': PlainLine,
    'arc': Arc,
    'slice': Slice
}

EFFECT_GROUPS = {
    'bow_sparks': {
        'base': [
            ['curved_spark', math.pi / 8, math.pi / 120, 3, 5, 0.4, 1],
            ['curved_spark', -math.pi / 8, -math.pi / 120, 3, 5, 0.4, 1],
            ['curved_spark', 0, 0, 3, 4, 0.2, 1],
            # ['curved_spark', math.radians(140), 0, 1, 15, 0.1, 1],
            # ['curved_spark', math.radians(220), 0, 1, 15, 0.1, 1],
        ],
        'random': [
            [[[0, 0], [0, 0]], [math.pi / 4, -math.pi / 8], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
            [[[0, 0], [0, 0]], [math.pi / 4, -math.pi / 8], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
            [[[0, 0], [0, 0]], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
            # [[[0, 0], [0, 0]], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
            # [[[0, 0], [0, 0]], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
        ],
    },
    'arrow_impact_sparks': {
        'base': [
            ['curved_spark', 0, 0, 2, 3, 0.1, 0.9],
        ],
        'random': [
            [[[0, 0], [0, 0]], [math.pi * 3 / 4, math.pi * 5 / 8], [0, 0], [2, 0], [1, 0], [0.3, 0], [0, 0]],
        ],
    },
    'previous_dash_sparks': {
        'base': [
            ['curved_spark', 0, 0, 2, 6, 0.08, 0.9],
        ],
        'random': [
            [[[0, 0], [0, 0]], [math.pi * 3 / 4, math.pi * 5 / 8], [0, 0], [2, 0], [1, 0], [0.3, 0], [0, 0]],
        ],
    },
    'dash_sparks': {
        'base': [
            ['curved_spark', 0, 0, 4, 1.5, 0.02, 0.9],
        ],
        'random': [
            [[[0, 0], [0, 0]], [math.pi * 3 / 4, math.pi * 5 / 8], [0, 0], [2, 0], [1, 0], [0.3, 0], [0, 0]],
        ],
    },
    'dash_sparks_2': {
        'base': [
            ['curved_spark', 0, 0, 4, 3, 0.02, 0.9],
        ],
        'random': [
            [[[0, 0], [0, 0]], [math.pi * 3 / 4, math.pi * 5 / 8], [0, 0], [2, 0], [1, 0], [0.3, 0], [0, 0]],
        ],
    }
}

class VFX:
    def __init__(self):
        self.effects_front = []
        self.effects_back = []

    def update(self):
        for group in [self.effects_front, self.effects_back]:
            for i, effect in itr(group):
                alive = effect.update()
                if not alive:
                    group.pop(i)

    def render_front(self, surf, offset=(0, 0)):
        for effect in self.effects_front:
            effect.render(surf, offset)

    def render_back(self, surf, offset=(0, 0)):
        for effect in self.effects_back:
            effect.render(surf, offset)

    def spawn_vfx(self, effect_type, *args, layer='back', **kwargs):
        if layer == 'front':
            self.effects_front.append(VFX_TYPES[effect_type](*args, **kwargs))
        if layer == 'back':
            self.effects_back.append(VFX_TYPES[effect_type](*args, **kwargs))

    def get_last_added(self, layer='front'):
        if layer == 'front':
            return self.effects_front[-1]
        if layer == 'back':
            return self.effects_back[-1]

    def spawn_group(self, group_type, position, rotation, layer='back', color=(255, 255, 255)):
        for i, particle in itr(EFFECT_GROUPS[group_type]['base']):
            effect_type = particle[0]
            particle = particle[1:]
            particle_data = [list(position)] + particle.copy()
            particle_data[1] += rotation
            random_data = EFFECT_GROUPS[group_type]['random'][i]
            particle_data[0][0] += rdm(*random_data[0][0])
            particle_data[0][1] += rdm(*random_data[0][1])
            for j in range(len(random_data) - 1):
                particle_data[j + 1] += rdm(*random_data[j + 1])
            if layer == 'front':
                self.effects_front.append(VFX_TYPES[effect_type](*particle_data, color))
            if layer == 'back':
                self.effects_back.append(VFX_TYPES[effect_type](*particle_data, color))

class Item:
    def __init__(self, directory, owner_ammo, type, config, entities, owner, amount=1):
        self.directory = pygame.image.load(directory).convert_alpha()
        self.type = type
        self.amount = amount
        self.entities = entities
        self.config = config
        self.owner_ammo = owner_ammo
        self.owner = owner

class Weapon(Item):
    def __init__(self, directory, owner_ammo, type, config, entities, owner, amount=1):
        super().__init__(directory, owner_ammo, type, config, entities, owner, amount)
        # self.type = type
        # self.directory = pygame.image.load(directory)
        self.rotation = 0
        self.aim_dis = 0
        self.capacity = self.config[self.type]["capacity"]
        self.ammo = self.capacity
        self.ammo_type = self.config[self.type]["ammo_type"]
        self.projectile_type = self.config[self.type]["projectile_type"]
        self.reload_method = self.config[self.type]["reload"]
        self.attack_rate = self.config[self.type]["attack_rate"]
        self.accuracy = self.config[self.type]["accuracy"]
        self.controls = self.config[self.type]["controls"]
        self.last_attack = 0

    def reload(self, particles, player, player_pos, player_direction, projectile_tiles, particle_images, global_time):
        self.particles = particles
        self.player_pos = player_pos
        self.projectile_tiles = projectile_tiles
        self.player = player
        self.player_direction = player_direction
        self.particles = particles
        self.particle_images = particle_images

        if (self.ammo < self.capacity) and (self.owner_ammo[self.ammo_type] > 0):
            dif = min(self.owner_ammo[self.ammo_type], self.capacity - self.ammo)
            self.ammo += dif
            self.owner_ammo[self.ammo_type] -= dif

            if self.reload_method in ["shells", "shotgun", "double_barrel"]:
                for i in range(dif):
                    if self.reload_method == "shells":
                        self.particles.add_particles('foreground', (self.player.get_center()[0], self.player_pos[1] + 5), 'shells', [-random.randint(1, 6) * self.player_direction, -random.randint(1, 8)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(255, 197, 0))
                    if self.reload_method == "double_barrel":
                        self.particles.add_particles('foreground', (self.player.get_center()[0], self.player_pos[1] + 5), 'shotgun_shells', [-random.randint(2, 4) * self.player_direction, -random.randint(1, 8)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(214, 61, 61))
                if self.reload_method == "shotgun":
                    self.particles.add_particles('foreground', (self.player.get_center()[0], self.player_pos[1] + 5), 'shotgun_shells', [-random.randint(2, 4) * self.player_direction, -random.randint(1, 8)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(214, 61, 61))
            if self.reload_method in ["mag", "pistol", "p90", "smg", "hornet"]:
                self.particles.add_particles('foreground', (self.player.get_center()[0]+10, self.player_pos[1]), self.reload_method, [-5 * self.player_direction, -random.randint(3, 5)], 0.002, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(32, 42, 92))
            if self.reload_method == "uzi":
                for i in range(2):
                    self.particles.add_particles('foreground', (self.player.get_center()[0]+10, self.player_pos[1]), 'uzi', [-5 * self.player_direction, -random.randint(3, 5)], 0.002, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(32, 42, 92))
                # add 35 to the y axis to have it be at the actual mag well

    def attack(self, projectiles, vfx, render_pos, player_pos, projectile_tiles, gun_config, player, player_direction, particles, particle_images, global_time):
        self.projectiles = projectiles
        self.vfx = vfx
        self.render_pos = render_pos
        self.player_pos = player_pos
        self.projectile_tiles = projectile_tiles
        self.gun_config = gun_config
        self.player = player
        self.player_direction = player_direction
        self.particles = particles
        self.particle_images = particle_images

        angle_offset = (1 - self.accuracy) * math.pi

        if (self.ammo > 0) and (time.time() - self.last_attack > self.attack_rate):
            gunshot_sound.play()
            if self.type not in ["uzi"]:
                self.ammo -= 1
            self.last_attack = time.time()
            if self.type not in ["shotgun", "double_barrel"]:
                self.projectiles.append(Projectile(self.projectile_type, self.render_pos.copy(), math.radians(self.rotation) - angle_offset + random.random() * angle_offset * 2, random.randint(8, 11), self.gun_config, self.player_pos, self.entities, self.projectile_tiles, self.player))
                if self.type == "uzi":
                    self.ammo -= 2
                    self.projectiles.append(Projectile(self.projectile_type, [self.render_pos.copy()[0], self.render_pos.copy()[1]+2], math.radians(self.rotation) - angle_offset + random.random() * angle_offset * 2, random.randint(11, 14), self.gun_config, self.player_pos, self.entities, self.projectile_tiles, self.player))
                    self.projectiles.append(Projectile(self.projectile_type, [self.render_pos.copy()[0], self.render_pos.copy()[1]-5], math.radians(self.rotation) - angle_offset + random.random() * angle_offset * 2, random.randint(11, 14), self.gun_config, self.player_pos, self.entities, self.projectile_tiles, self.player))
            else:
                for i in range(5):
                    self.projectiles.append(Projectile(self.projectile_type, self.render_pos.copy(), math.radians(self.rotation) - angle_offset + random.random() * angle_offset * 2 + random.randint(0, 75) / 100 - 0.5, 10, self.gun_config, self.player_pos, self.entities, self.projectile_tiles, self.player))

            # self.vfx.spawn_vfx('arc', self.player.get_center().copy(), 2, random.random() * 3, math.radians(self.rotation-20), 4, random.random() * 6 + 100, 0.5, start=0, end=0.5, duration=1, arc_stretch=200, motion=random.randint(300, 450), decay=['down', 100], color=(196, 42, 42), fade=0.5)
            self.vfx.spawn_group('bow_sparks', advance(self.render_pos.copy(), math.radians(self.rotation), 15), math.radians(self.rotation), layer="back")
            self.vfx.spawn_group('bow_sparks', advance(self.render_pos.copy(), math.radians(self.rotation), 15), math.radians(self.rotation), layer="back")

            if self.reload_method == "shotgun":
                self.particles.add_particles('foreground', (self.player.get_center()[0], self.player_pos[1] + random.randint(2, 6)), 'shotgun_shells', [-5 * self.player_direction, -random.randint(1, 2)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(214, 61, 61))

            if self.reload_method in ["clip", "mag", "p90", "smg", "hornet"]:
                self.particles.add_particles('foreground', (self.player.get_center()[0]+10, self.player_pos[1] + random.randint(2, 6)), 'shells', [-5 * self.player_direction, -random.randint(1, 2)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(255, 197, 0))
            else:
                if self.reload_method not in ["shotgun", "double_barrel", "shells"]:
                    for i in range(2):
                        self.particles.add_particles('foreground', (self.player.get_center()[0]+10, self.player_pos[1] + random.randint(2, 6)), 'shells', [-5 * self.player_direction, -random.randint(1, 2)], 0.003, 0, self.projectile_tiles, self.particle_images, global_time, physics=self.projectile_tiles, custom_color=(255, 197, 0))

    def render(self, surf, loc):
        img = self.directory.copy()
        if (self.rotation % 360 < 270) and (self.rotation % 360 > 90):
            img = pygame.transform.flip(img, False, True)
        img = pygame.transform.rotate(img, -self.rotation)
        surf.blit(img, (loc[0] - img.get_width() // 2, loc[1] - img.get_height() // 2))

class Projectile:
    def __init__(self, type, pos, rot, speed, config, player_pos, entities, game_map, owner):
        self.type = type
        self.pos = pos
        self.rotation = rot
        self.speed = speed
        self.player_pos = player_pos
        self.game_map = game_map
        self.entities = entities
        self.config = config[self.type]
        self.owner = owner

        advance(self.pos, self.rotation, self.config["spawn_advance"])

    def move(self):
        directions = {k: False for k in ['top', 'left', 'right', 'bottom']}

        cx = math.cos(self.rotation) * self.speed
        self.pos[0] += cx
        if self.game_map.tile_collide(self.pos):
            if cx > 0:
                directions['right'] = True
            else:
                directions['left'] = True
            return directions

        cy = math.sin(self.rotation) * self.speed
        self.pos[1] += cy
        if self.game_map.tile_collide(self.pos):
            if cy > 0:
                directions['bottom'] = True
            else:
                directions['top'] = True
        return directions

        # advance(self.pos, self.rotation, self.speed)

    def update(self):
        in_range = player.in_range(self.pos, 600)
        if not in_range:
            return False

        if self.config['group'] == 'heavy_blob':
            vec = to_cart(self.rotation, self.speed)
            vec[1] = min(10, vec[1] + (dt) * 10)
            self.rotation, self.speed = to_polar(vec)

        collisions = self.move()
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
                    vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), angle, layer="back")
                return False
            elif self.config['group'] == 'heavy_blob':
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
                for i in range(random.randint(2, 3)):
                    vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), self.rotation, layer="back")
                advance(self.pos, self.rotation, 2)

        for entity in self.entities:
            for i in entity:
                i_rect = i.rect()
                if i != self.owner:
                    if i_rect.collidepoint(self.pos):
                        vfx.spawn_vfx('slice', self.pos.copy(), random.random() * math.pi / 4 - math.pi / 8 + self.rotation, 20 * random.random() + 40, 1.5, 3, 0.1)
                        i.x += math.cos(self.rotation) * 300 * (dt) * self.config['knockback']
                        i.y += math.sin(self.rotation) * 300 * (dt) * self.config['knockback']
                        i.damage(self.config['power'])
                        if random.randint(1, 3) == 1:
                            add_freeze(0.2, 0.2)
                        for i in range(random.randint(5, 20)):
                            vfx.spawn_group('arrow_impact_sparks', self.pos.copy(), self.rotation + math.pi)
                        return False
        return True

    def render(self, surf, offset=(0, 0)):
        render_pos = [self.pos[0] - offset[0], self.pos[1] - offset[1]]
        if self.config["shape"]:
            if self.config["shape"][0] == "line":
                pygame.draw.line(surf, self.config["shape"][1], render_pos, advance(render_pos.copy(), self.rotation, self.config["shape"][2]), self.config["shape"][3])
        else:
            img = pygame.image.load('data/images/projectiles/' + self.type + '.png').convert_alpha()
            render_pos[0] -= img.get_width()
            render_pos[1] -= img.get_height()
            display.blit(img, render_pos)

class Hitbox:
    def __init__(self, config, hitbox_type, entities, duration=-1, rect=None, tracked=None, owner=None, angle=None):
        if tracked:
            self.mode = "tracked"
            self.tracked = tracked
        else:
            self.mode = "rect"
            self.rect = rect
        self.duration = duration
        self.hitbox_type = hitbox_type
        self.config = config[hitbox_type]
        self.entities = entities
        self.owner = owner
        self.angle = angle
    
    def update(self):
        if self.mode == "tracked":
            tracked_mask, offset = self.tracked.create_mask()
            mask_surf = tracked_mask.to_surface(setcolor=(255, 0, 0, 255), unsetcolor=(1, 255, 0, 255))
            # display.blit(mask_surf, (offset[0] - true_scroll[0], offset[1] - true_scroll[1]))
            
            for entity_list in self.entities:
                for entity in entity_list:
                    if entity != self.owner:
                        mask_surf = entity.mask.to_surface(setcolor=(255, 0, 0, 255), unsetcolor=(1, 255, 0, 255))
                        entity_offset = entity.calculate_render_offset()
                        collision = tracked_mask.overlap(entity.mask, (int(entity.x - offset[0]), int(entity.y - offset[1])))
                        # collision_point = (entity.x + collision[0], entity.y + collision[1])
                        if collision:
                            collision_point = [offset[0] + collision[0], offset[1] + collision[1]]
                            if self.angle:
                                vfx.spawn_vfx('slice', collision_point.copy(), random.random() * math.pi / 4 - math.pi / 8 + self.angle, 20 * random.random() + 40, 1.5, 3, 0.1)
                                entity.x += math.cos(self.angle) * 300 * (dt) * self.config['knockback']
                                entity.y += math.sin(self.angle) * 300 * (dt) * self.config['knockback']
                                entity.damage(self.config['power'])
                                if random.randint(1, 3) == 1:
                                    add_freeze(0.2, 0.2)
                                for i in range(random.randint(15, 30)):
                                    vfx.spawn_group('arrow_impact_sparks', collision_point.copy(), self.angle + math.pi)
                            return False
                        # display.blit(mask_surf, (entity.x  - true_scroll[0], entity.y - true_scroll[1]))
            return self.tracked.alive

class Hitboxes:
    def __init__(self):
        self.hitboxes = []

    def update(self):
        for i, hitbox in itr(self.hitboxes):
            alive = hitbox.update()
            if not alive:
                self.hitboxes.pop(i)

    def add_hitbox(self, *args, **kwargs):
        self.hitboxes.append(Hitbox(*args, **kwargs))

hitboxes = Hitboxes()

class SwordWeapon(Weapon):
    def attack(self, projectiles, vfx, render_pos, player_pos, projectile_tiles, gun_config, player, player_direction, particles, particle_images, global_time):
        self.player = player
        self.vfx = vfx
        self.invisible = 0.2
        if self.player.flip:
            self.vfx.spawn_vfx('arc', self.player.get_center().copy(), 2, random.random() * 3, math.radians(self.rotation-20), 4, random.random() * 6 + 100, 0.5, start=0, end=0.5, duration=0.7, arc_stretch=200, motion=random.randint(300, 450), decay=['down', 100], color=(255, 255, 255), fade=0.5, angle_width = 0.4, layer="front")
        else:
            self.vfx.spawn_vfx('arc', self.player.get_center().copy(), 2, random.random() * 3, math.radians(self.rotation+20), 4, random.random() * 6 + 100, 0.5, start=0.5, end=1, duration=0.7, arc_stretch=200, motion=random.randint(300, 450), decay=['up', 100], color=(255, 255, 255), fade=0.5, angle_width = 0.4, layer="front")
        arc_mask, offset = self.vfx.get_last_added().create_mask()
        hitboxes.add_hitbox(hitboxes_config, 'katana', self.entities, tracked=self.vfx.get_last_added(), owner=self.owner, angle=math.radians(self.rotation))
        # mask_surf = arc_mask.to_surface()
        # display.blit(mask_surf, (offset[0] - true_scroll[0], offset[1] - true_scroll[1]))

class Skill:
    def __init__(self, owner, skill_type):
        self.owner = owner
        self.skill_type = skill_type
        self.charges_max = 1
        self.charges = self.charges_max
        self.charge_rate = 1

    def update(self):
        if self.charges < self.charges_max:
            self.charge += 0.06
            if self.charge > self.charge_rate:
                self.charge = 0
                self.charges += 1

    def use(self):
        if self.charges:
            self.charges -= 1
            return True
        else:
            return False

    def render(self, dir, loc):
        img = dir[self.skill_type].copy()
        if not self.charges:
            progress = self.charge / self.charge_rate
            charge_surf = pygame.Surface((img.get_width(), int(img.get_height() * (1 - progress))))
            charge_surf.fill((100, 100, 100))
            img.blit(charge_surf, (0, img.get_height() - charge_surf.get_height()), special_flags=pygame.BLEND_RGBA_SUB)
        display.blit(img, loc)
        # if self.charges >= 1:
            # small_font.render(display, str(self.charges), (loc[0] + img.get_width() // 2 - 5 // 2, loc[1] - 9))

class DashSkill(Skill):
    def __init__(self, owner):
        super().__init__(owner, 'dash')
        self.dash_timer = 0
        self.charges_max = 4
        self.charges = self.charges_max
        self.charge_rate = 6
        self.charge = 0

    def update(self, gravity_on, player_movment, destruction_particles, vfx, particles, tile_map, particle_img, global_time):
        super().update()
        self.dash_timer -= 0.06
        self.dash_timer = max(0, self.dash_timer)

        if self.dash_timer:
            player_movement[0] = normalize(player_movement[0], 1750) * dt
            player_movement[1] = normalize(player_movement[1], 1750) * dt

            img = self.owner.get_current_img().copy()
            img.set_alpha(random.randint(70, 90))
            for i in range(2):
                vfx.spawn_group('dash_sparks', self.owner.get_center().copy(), angle, layer="back")
                vfx.spawn_group('dash_sparks_2', self.owner.get_center().copy(), angle, color=(237, 28, 36), layer="back")
            destruction_particles.add_particle(img, self.owner.get_center().copy(), [random.random() * 3 * angle, random.random() * random.randint(-3, 3),random.random() * 3], duration=random.randint(1,5), gravity=False)
            
        gravity_on = not bool(self.dash_timer)

        # return gravity_on, player_movement

    def use(self, player_movement, angle, vfx):
        if super().use():
            player_movement[0] = math.cos(angle) * 200
            player_movement[1] = math.sin(angle) * 200
            self.dash_timer = 0.6
            for i in range(random.randint(30, 50)):
                vfx.spawn_group('previous_dash_sparks', self.owner.get_center().copy(), angle, layer="back")

        # return player_movement

class Blink(Skill):
    def __init__(self, owner):
        super().__init__(owner, 'blink')

        self.charges_max = 7
        self.charges = self.charges_max
        self.charge_rate = 7
        self.charge = 0

        self.teleport_timer = 0

    def update(self, gravity_on, player_movement, destruction_particles, vfx, particles, tile_map, particle_img, global_time):
        super().update()

        dt = 0.06

        if self.teleport_timer:
            self.teleport_timer = max(0, self.teleport_timer - dt)

            angle = random.random() * math.pi * 2
            speed = 0

            c = random.choice([(3, 6, 37), (3, 6, 37), (235, 237, 233), (230, 5, 5)])
            particles.add_particles('foreground', self.owner.get_center(), 'p', [math.cos(angle) * speed, math.sin(angle) * speed], 0.04, random.random() * 4 + 2, tile_map, particle_img, global_time, custom_color=c)
            
            if not self.teleport_timer:
                player_movement = [0, 0]

                for i in range(50):
                    angle = random.random() * math.pi * 2
                    speed = random.choice([0.5, 1.5])

                    c = random.choice([(3, 6, 37), (3, 6, 37), (235, 237, 233), (230, 5, 5)])
                    particles.add_particles('foreground', self.owner.get_center(), 'p', [math.cos(angle) * speed, math.sin(angle) * speed], 0.04, random.random() * 4 + 2, tile_map, particle_img, global_time, custom_color=c)
            
            else:
                player_movement[0] = math.cos(math.radians(weapon.rotation)) * 200
                player_movement[1] = math.sin(math.radians(weapon.rotation)) * 200

            self.owner.visible = False

    def use(self, particles, weapon, tile_map, particle_img, global_time):
        if super().use():
            if weapon:
                self.teleport_timer = 0.1

                for i in range(50):
                    angle = random.random() * math.pi * 2
                    speed = random.choice([0.5, 1.5])

                    c = random.choice([(3, 6, 37), (3, 6, 37), (235, 237, 233), (230, 5, 5)])
                    particles.add_particles('foreground', self.owner.get_center(), 'p', [math.cos(angle) * speed, math.sin(angle) * speed], 0.04, random.random() * 4 + 2, tile_map, particle_img, global_time, custom_color=c)
 
                # teleport_dis = min(weapon.aim_dis, 150)
                # player_movement[0] += math.cos(math.radians(weapon.rotation)) * teleport_dis
                # player_movement[1] += math.sin(math.radians(weapon.rotation)) * teleport_dis


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

SKILLS = {
    'dash': DashSkill,
    'blink': Blink
}

leaves = []
load_particle_images('data/images/particles')

spritesheets, spritesheets_data = spritesheet_loader.load_spritesheets('data/images/spritesheets/')
particles_m.load_particle_images('data/images/particles')
particles = []

foliage_animations = [AnimatedFoliage(load_img('data/images/foliage/' + str(i) + '.png', colorkey=(0, 0, 0)), [[26, 33, 64], [58, 21, 27], [69, 24, 11], [92, 33, 7], [111, 22, 13], [135, 51, 43], [137, 9, 9], [157, 30, 30], [156, 24, 24], [171, 25, 25], [199, 28, 28], [234, 114, 34], [238, 33, 33]], motion_scale=0.3) for i in range(1)]

grass_manager = GrassManager('data/images/grass', tile_size=16)

level_map = tile_map.TileMap((TILE_SIZE, TILE_SIZE), display.get_size())
level_map.load_map('save.json')

level_map.load_grass(grass_manager)

class Fly:
    def __init__(self, data):
        self.data = data

soul_flies = []
for i in range(30):
    soul_flies.append(Fly([[random.random() * 300, random.random() * 200], random.random() * math.pi * 2, 0, random.random() * 0.5 + 0.2]))

light_mask_base = load_img('data/images/lights/light.png')
light_mask_base_blue = light_mask_base.copy()
light_mask_base_blue.fill((83, 145, 255))
light_mask_base_blue.blit(light_mask_base, (0, 0), special_flags=BLEND_RGBA_MULT)
light_mask_full = pygame.transform.scale(light_mask_base, (400, 300))
light_mask_full.blit(light_mask_full, (0, 0), special_flags=BLEND_RGBA_ADD)
light_masks = []
light_masks_blue = []
for radius in range(1, 850):
    light_masks.append(pygame.transform.scale(light_mask_base, (radius, radius)))
for radius in range(1, 50):
    light_masks_blue.append(pygame.transform.scale(light_mask_base_blue, (radius, radius)))

vfx = VFX()
destruction_particles = dp.DestructionParticles()
particles_adv = p.ParticleManager()
Minimap = mp.Minimap(true_scroll, level_map)

particle_images = {folder : load_dir_list('data/images/particles/' + folder) for folder in os.listdir('data/images/particles')}

e.load_animations('data/images/entities/')
misc = load_dir('data/images/misc')
skills_images = load_dir('data/images/skills')

jump_sound = pygame.mixer.Sound('data/audio/jump.wav')
grass_sounds = [pygame.mixer.Sound('data/audio/grass_0.wav'),pygame.mixer.Sound('data/audio/grass_1.wav')]
gunshot_sound = pygame.mixer.Sound('data/audio/gunshot.wav')
grass_sounds[0].set_volume(0.2)
grass_sounds[1].set_volume(0.2)

pygame.mixer.music.load('data/audio/music.wav')
pygame.mixer.music.play(-1)

grass_sound_timer = 0

# player
player_max_health = entities_config['player']['base_health']
player_health = player_max_health
player = e.entity(1, 0,24,24,'player',health=player_health)

player_list = []
player_list.append(player)
player_size = [player.size_x, player.size_y]
projectiles = []
player_state = {
    "reload": False
}

tutorial = 2
tutorial_img = load_img('data/images/tutorial.png', colorkey=(0, 0, 0))
title_notice = 1
title = load_img('data/images/title.png', colorkey=(0, 0, 0))
gold = 0
gold_particles = []
gold_img = load_img('data/images/misc/gold.png', colorkey=(0, 0, 0))
gold_s = load_snd('gold')

dash = 0
max_jumps = 8
jumps = max_jumps
jumping = False
falling = False
generate_ground_particles = 0.4

skills = [SKILLS['dash'](player), SKILLS['blink'](player), None, None]
gravity_on = True

# item drops
item_drops = []
item_drops.append(ItemDrop(Item('data/images/entities/battle_rifle/idle/idle_0.png', None, 'item', None, None, None, amount=1), level_map, 100, -100, 45, 17, 'battle_rifle'))

tooltips = ToolTips()
hover_item = None

# enemy stuff
metal_heads = []
for i in range(8):
    metal_head = e.entity(random.randint(-8865, -8765), random.randint(-3100, -3050), 17, 22, 'metalhead', health=entities_config['metalhead']['base_health'])
    metal_heads.append(metal_head)
metal_head_bob_timer = 0
metal_head_attack_timer = 0
metal_head_hover_distance = random.randint(50, 90)
metal_head_speed = random.randint(50, 80)

# adding the entities to the entities
entities = []
entities.append(metal_heads)
entities.append(player_list)
entities.append(item_drops)

# Weapons stuff
ammo = {
    'medium': 500,
}
# inventory = {
#     ('active', 0): Weapon('data/images/gun_obj/smg.png', ammo, 'smg', gun_var_config)
# }
inventory = {}
player_give_item(inventory, Weapon('data/images/gun_obj/rifle.png', ammo, 'rifle', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/smg.png', ammo, 'smg', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/p90.png', ammo, 'p90', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/uzi.png', ammo, 'uzi', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/hornet.png', ammo, 'hornet', gun_var_config, entities, player))
# player_give_item(inventory, Weapon('data/images/gun_obj/small_revolver.png', ammo, 'small_revolver', gun_var_config, entities, player))
# player_give_item(inventory, Weapon('data/images/gun_obj/gold_revolver.png', ammo, 'gold_revolver', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/pistol.png', ammo, 'pistol', gun_var_config, entities, player))
player_give_item(inventory, Weapon('data/images/gun_obj/revolver.png', ammo, 'revolver', gun_var_config, entities, player))
# player_give_item(inventory, Weapon('data/images/gun_obj/shotgun.png', ammo, 'shotgun', gun_var_config, entities, player))
# player_give_item(inventory, Weapon('data/images/gun_obj/double_barrel.png', ammo, 'double_barrel', gun_var_config, entities, player))
# player_give_item(inventory, Weapon('data/images/gun_obj/deaggle.png', ammo, 'deaggle', gun_var_config, entities))
# player_give_item(inventory, Weapon('data/images/gun_obj/flintknock.png', ammo, 'flintknock', gun_var_config, entities))
# player_give_item(inventory, SwordWeapon('data/images/gun_obj/katana.png', ammo, 'katana', gun_var_config, entities, player))

selected_slot = ('active', 0)

# background_objects = [[0.25,[120,10,70,400]],[0.25,[280,30,40,400]],[0.5,[30,40,40,400]],[0.5,[130,90,100,400]],[0.5,[300,80,120,400]]]

mouse_state = {
    "left": False,
    "right": False,
    "left_hold": False,
    "right_hold": False,
    "left_release": False,
    "right_release": False,
    "scroll_up": False,
    "scroll_down": False
}

keyboard_state = {
    'left_ctrl': False
}

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
            pygame.draw.rect(square_surf, (45, 13, 55), pygame.Rect(size * 0.1, size * 0.1, size, size), width = self.width)
                
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
                self.squares.append(Square([random.random() * display.get_width(), random.random() * display.get_height()], scroll, random.randint(5, 20), random.randint(15, 60)))

        self.spawn_timer += 0.06
        while self.spawn_timer > 0.2:
            self.spawn_timer -= 0.2
            self.squares.append(Square([random.random() * display.get_width(), random.random() * display.get_height()], scroll, random.randint(5, 20), random.randint(15, 60)))

        for i, square in itr(self.squares):
            alive = square.update(dt)
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

class AnimatedTileData:
    def __init__(self, level_map):
        self.level_map = level_map
        self.tiles = []

        self.load_tiles()

    def load_tiles(self):
        self.entities = self.level_map.load_entities()
        for entity in self.entities:
            entity_type = entity[2]['type'][1]
            if entity_type == 0:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (224, 157), 'rotating_obj'))
            if entity_type == 1:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (32, 49), 'cat'))
            if entity_type == 3:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (72, 31), 'roasting'))
            if entity_type == 4:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (27, 60), 'cat_statue'))
            if entity_type == 5:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (17, 16), 'cat_up'))
            if entity_type == 6:
                self.tiles.append(Entity(animation_manager, entity[2]['raw'][0], (80, 104), 'portal'))
            
        return self.tiles

background_entities = AnimatedTileData(level_map)
# animated_tiles = background_entities.load_tiles()

while True: # game loop

    global_time += 1
    terrain_particles_queue = []
    # time.sleep(0.1)

    weapon = player_weapon(inventory, selected_slot)

    player_pos = [player.x, player.y]

    mouse_pos = pygame.mouse.get_pos()
    display.fill((49, 42, 80)) # clear screen by filling it with a color
    light_surf = display.copy()
    light_surf.fill((5, 15, 35))

    if grass_sound_timer > 0:
        grass_sound_timer -= 1

    true_scroll[0] += (player.x-true_scroll[0]-window_offset[0])/20
    true_scroll[1] += (player.y-true_scroll[1]-window_offset[1])/20
    scroll = true_scroll.copy()
    scroll[0] = int(scroll[0])
    scroll[1] = int(scroll[1])

    if random.random() < 0.1:
        if random.random() > 0.25:
            bg_bubbles.append([[random.random() * 600, 400], random.random() * 2.5 + 0.25, random.random() * 18 + 1, random.random() - 0.5])
        else:
            bg_bubbles.append([[random.random() * 600, 0], random.random() * -2.5 - 0.25, random.random() * 18 + 1, random.random() - 0.5])
    for i, bubble in sorted(enumerate(bg_bubbles), reverse=True):
        bg_bubble_particles.append([((bubble[0][0] + scroll[0] * bubble[3]) % 600, bubble[0][1]), bubble[2]])
        bubble[0][1] -= bubble[1]
        if (bubble[0][1] < 0) or (bubble[0][1] > 400):
            bg_bubbles.pop(i)

    for i, p in sorted(enumerate(bg_bubble_particles), reverse=True):
        pygame.draw.circle(display, (0, 0, 0), p[0], int(p[1]))
        p[1] -= 0.3
        if p[1] <= 0:
            bg_bubble_particles.pop(i)

    parallax = random.random()
    for i in range(2):
        bg_particles.append([[random.random() * display.get_width(), display.get_height() - height * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice([(0, 0, 0), (12, 10, 18)])])

    for i, p in sorted(enumerate(bg_particles), reverse=True):
        size = p[2]
        # if p[-1] != (0, 0, 0):
        #     size = size * 5 + 4
        p[2] -= 0.01
        p[0][1] -= p[3]
        if size < 1:
            display.set_at((int(p[0][0]), int(p[0][1] + height * p[1])), (0, 0, 0))
        else:
            if p[-1] != (0, 0, 0):
                pygame.draw.circle(display, p[-1], p[0], int(size), 4)
            else:
                pygame.draw.circle(display, p[-1], p[0], int(size))
        if size < 0:
            bg_particles.pop(i)

    background.update(scroll)
    background.render(display, scroll)

    background_offset = (background_offset + 0.25) % 30
    for i in range(18):
        pygame.draw.line(display, (35, 10, 43), (-10, int(i * 30 + background_offset - 20)), (display.get_width() + 20, int(i * 30 - 110 + background_offset)), 15)

    rects = [t[1] for t in level_map.get_nearby_rects(player.get_center())]

    for background_entity in background_entities.tiles:
        background_entity.update(dt)
        # background_entity.render(display, scroll)

    render_list = level_map.get_visible(scroll)
    for layer in render_list:
        layer_id = layer[0]
        for background_entity in background_entities.tiles:
                background_entity.render(display, scroll)
        for tile in layer[1]:
            if tile[1][0] == "foliage":
                seed = int(tile[0][1] * tile[0][0] + (tile[0][0] + 10000000) ** 1.2)
                foliage_animations[tile[1][1]].render(display, (tile[0][0] - scroll[0], tile[0][1] - scroll[1]), m_clock=global_time / 100, seed=seed)
                if random.random() < 0.2:
                    pos = foliage_animations[tile[1][1]].find_leaf_point() 
                    leaves.append(Particle(tile[0][0] + pos[0], tile[0][1] + pos[1], 'grass', [random.random() * 10 + 10, 8 + random.random() * 4], 0.7 + random.random() * 0.6, random.random() * 2, custom_color=random.choice([[26, 33, 64], [58, 21, 27], [69, 24, 11], [92, 33, 7], [111, 22, 13], [135, 51, 43], [137, 9, 9], [157, 30, 30], [156, 24, 24], [171, 25, 25], [199, 28, 28], [234, 114, 34], [238, 33, 33]])))
            else:
                offset = [0, 0]
                if tile[1][0] in spritesheets_data:
                    tile_id = str(tile[1][1]) + ';' + str(tile[1][2])
                    if tile_id in spritesheets_data[tile[1][0]]:
                        if 'tile_offset' in spritesheets_data[tile[1][0]][tile_id]:
                            offset = spritesheets_data[tile[1][0]][tile_id]['tile_offset']
                if tile[1][0] == "torches":
                    if random.randint(1, 4) == 1:
                        particles.append(particles_m.Particle(tile[0][0] + 7, tile[0][1] + 4, 'light', [random.randint(0, 10) / 15 - 0.5, random.randint(0, 20) / 10 - 2], 0.1, 3 + random.randint(0, 20) / 10, custom_color=random.choice([[52, 98, 252], [84, 122, 248], [84, 158, 248], [84, 194, 248], [141, 217, 255]])))
                if tile[1][0] == "fire_points":
                    if random.randint(1, 2) == 1:
                        particles.append(particles_m.Particle(tile[0][0] + 8, tile[0][1] + 6, 'light', [random.randint(0, 10) / 15 - 0.5, random.randint(0, 20) / 10 - 2], 0.1, 3 + random.randint(0, 20) / 10, custom_color=random.choice([[52, 98, 252], [84, 122, 248], [84, 158, 248], [84, 194, 248], [141, 217, 255]])))
                img = spritesheet_loader.get_img(spritesheets, tile[1])
                display.blit(img, (tile[0][0] - scroll[0] + offset[0], tile[0][1] - scroll[1] + offset[1])) 

    grass_manager.update_render(display, 1/60, offset=scroll.copy(), rot_function=lambda x, y: int((math.sin(x / 100 + global_time / 40) + 0.4) * 30) / 10)

    # torch particle lighting
    for i, particle in itr(particles):
        alive = particle.update(0.1)
        particle.draw(display, scroll)
        if particle.type == 'light':
            particles_m.blit_center_add(light_surf, particles_m.circle_surf(5 + particle.time_left * (math.sin(particle.random_constant * global_time * 0.01) + 3), (1 + particle.time_left * 0.2, 4 + particle.time_left * 0.4, 8 + particle.time_left * 0.6)), (particle.x-scroll[0], particle.y-scroll[1]))
        if not alive:
            particles.pop(i)

    mouse_state["left"] = False
    mouse_state["right"] = False
    mouse_state["left_release"] = False
    mouse_state["right_release"] = False
    mouse_state["scroll_up"] = False
    mouse_state["scroll_down"] = False
    player_state['reload'] = False

    keyboard_state['left_ctrl'] = False

    for event in pygame.event.get(): # event loop
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_p:
                pygame.mixer.music.fadeout(1000)
            if event.key == K_d:
                moving_right = True
            if event.key == K_a:
                moving_left = True
            if event.key == K_w or event.key == K_SPACE:
                if air_timer < 6:
                    if jumps:
                        jump_sound.play()
                        vertical_momentum = -500 * dt
                        jumps -= 1
                        jumping = True
                        if tutorial == 2:
                            tutorial = 1
            if event.key == K_e:
                player.set_pos(-500, 100)
            if event.key == K_r:
                player_state["reload"] = True
            if event.key == K_LCTRL:
                keyboard_state['left_ctrl'] = True
                # skills[1].use(player_movement, weapon, angle)
                
        if event.type == KEYUP:
            if event.key == K_d:
                moving_right = False
            if event.key == K_a:
                moving_left = False

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_state["left"] = True
                mouse_state["left_hold"] = True
                mouse_state["left_release"] = False
            if event.button == 3:
                mouse_state["right"] = True
                mouse_state["right_hold"] = True
            if event.button == 4:
                mouse_state["scroll_up"] = True
            if event.button == 5:
                mouse_state["scroll_down"] = True
        if event.type == MOUSEBUTTONUP:
            if event.button == 1:
                mouse_state["left_release"] = True
                mouse_state["left_hold"] = False
            if event.button == 3:
                mouse_state["right_release"] = True
                mouse_state["right_hold"] = False

    # player stuff
    player_movement = [0, 0]
    player_movement[0] = normalize(player_movement[0], 2500) * dt

    if moving_right == True:
        player_movement[0] += 250 * dt
    if moving_left == True:
        player_movement[0] -= 250 * dt

    angle = math.atan2(mouse_pos[1] - player.get_center()[1] + render_offset(true_scroll, window_offset)[1], mouse_pos[0] - player.get_center()[0] + render_offset(true_scroll, window_offset)[0])
    aim_dis = math.sqrt((mouse_pos[1] - player.get_center()[1] + render_offset(true_scroll, window_offset)[1]) ** 2 + (mouse_pos[0] - player.get_center()[0] + render_offset(true_scroll, window_offset)[0]) ** 2)
    print(render_offset(true_scroll, window_offset))

    if gravity_on:
        player_movement[1] += vertical_momentum
        vertical_momentum += 34 * dt
        if vertical_momentum > 300 * dt:
            vertical_momentum = 300 * dt
            falling = True
        else:
            falling = False

    if player_movement[0] != 0 and jumping == False and falling == False:
        player.set_action('run')
    if player_movement[0] == 0 and jumping == False and falling == False:
        player.set_action('idle')
    if jumping == True and falling == False:
        player.set_action('jump')
        if jumps < 7:
            if moving_right == True:
                target_rot = 360
                if player.rotation != target_rot:
                    player.rotation += 60
            if moving_left == True:
                target_rot = -360
                if player.rotation != target_rot:
                    player.rotation -= 60
            if (moving_right == False and moving_left == False):
                player.rotation = 0
    if falling:
        player.set_action('fall')

    # if jumping:
    #     player.set_action('jump')
        # if grass_sound_timer == 0:
        #     grass_sound_timer = 30
        #     random.choice(grass_sounds).play()

    for skill in skills:
        if skill:
            skill.update(gravity_on, player_movement, destruction_particles, vfx, particles_adv, level_map, particle_images, global_time)

    if mouse_state["right"]:
        # skills[1].use(player_movement, weapon, angle)
        skills[0].use(player_movement, angle, vfx)
        style_meter.remove_style(10)

    if keyboard_state['left_ctrl']:
        skills[1].use(particles_adv, weapon, level_map, particle_images, global_time)

    collision_types = player.move(player_movement, physical_rect_filter(level_map.get_nearby_rects(player.get_center())))

    if collision_types['bottom'] == True:
        player.rotation = 0
        jumping = False
        air_timer = 0
        vertical_momentum = 0
        jumps = max_jumps
        if player_movement[0] != 0:
            if random.random() < generate_ground_particles:
                base_pos = [player.get_center()[0], (player.get_center()[1] + 12) + int(random.random() * 2.5 + 2)]
                terrain_particles_queue.append((base_pos, player_movement))
    # else:  
        # jumps = max_jumps
    #     air_timer += 1

    # player.change_frame(1)
    # if player.visible:
        # player.display(display,scroll)
    
    grass_manager.apply_force(player.get_center(), 8, 16)
    hitboxes.update()

    generate_terrain_particles(display, terrain_particles_queue, particles_adv, scroll, level_map, particle_images, global_time)

    # inventory stuff
    if mouse_state["scroll_up"]:
        selected_slot = step_slot(inventory, selected_slot, -1)
    if mouse_state["scroll_down"]:
        selected_slot = step_slot(inventory, selected_slot, 1)

    if (weapon.rotation % 360 < 270) and (weapon.rotation % 360 > 90):
        player.set_flip(True)
        player_direction = -1
    else:
        player.set_flip(False)
        player_direction = 1

    closest_item = [99999, None]
    for item in item_drops:
        if item.item_data.type == 'item':
            dis = item.get_distance(player_pos)
            if (closest_item[0] > dis) and (dis < 50):
                closest_item = [dis, item]
    if closest_item[1] and ((hover_item == None) or (hover_item[3] != closest_item[1])):
        hover_item = tooltips.add_tooltip(closest_item[1].item_data.type, [closest_item[1].get_center()[0], closest_item[1].y - 2], closest_item[1])
    elif closest_item[1] == None:
        if hover_item:
            hover_item[1] = -1
            hover_item = None
    
    tooltips.update(dt)
    tooltips.render(display, scroll, small_font)

    for item in item_drops:
        grass_manager.apply_force(item.get_center(), 8, 16)

    # render projectiles from weapon
    for i, projectile in itr(projectiles):
        alive = projectile.update()
        if not alive:
            projectiles.pop(i)
    for projectile in projectiles:
        projectile.render(display, scroll)

    # enemies
    for metal_head in metal_heads:
        movement = [0, 0]
        velocity = [0, 0]
        hover_rate = 1

        metal_head_bob_timer += (dt)
        metal_head_attack_timer -= 0.02

        velocity[0] = normalize(velocity[0], 350 * (dt))
        velocity[1] = normalize(velocity[1], 350 * (dt))
        movement[0] += velocity[0] * (dt)
        movement[1] += velocity[1] * (dt)

        metal_head_angle = metal_head.get_angle_xy(player)
        target_position = [(player.x + math.cos(angle + math.pi) * metal_head_hover_distance) * dt, (player.y + math.sin(angle + math.pi) * metal_head_hover_distance) * dt]
        target_position[1] += math.sin(metal_head_bob_timer / hover_rate) * 5

        target_angle = metal_head.get_angle_pos(target_position)
        target_pos_dis = metal_head.get_distance(target_position)
        if target_pos_dis > metal_head_speed:
            movement[0] += math.cos(target_angle) * metal_head_speed * (dt)
            movement[1] += math.sin(target_angle) * metal_head_speed * (dt)
        else:
            movement = [target_position.copy()[0] * (dt), target_position.copy()[1] * (dt)]

        dis = metal_head.get_distance(player.get_center())
        if dis > 120:
            if metal_head_attack_timer < 0:
                projectiles.append(Projectile('heavy_blob', metal_head.get_center(), metal_head_angle + random.randint(0, 50) / 100 - 0.25, 7, gun_config, [metal_head.x, metal_head.y], entities, level_map, metal_head))
                metal_head_attack_timer = 1

        collision_types = metal_head.move(movement, rects)

        if metal_head.health <= 0:
            for i in range(random.randint(2, 4)):
                x = random.randint(0,4)
                gold_particles.append([metal_head.x+x-scroll[0],metal_head.y+7+random.randint(0,6)-scroll[1],[x-4,-random.randint(3,6)],random.randint(0,30)])
            metal_head.die(metal_head, metal_head.get_current_img(), [metal_head.x, metal_head.y], destruction_particles, vfx)

    if screen_shake > 0:
        screen_shake -= 1

    screen_render_offset = [0, 0]
    if screen_shake:
        screen_render_offset[0] = random.randint(0, 8) - 4
        screen_render_offset[1] = random.randint(0, 8) - 4

    # particle stuff
    particles_adv.update()
    particles_adv.render('foreground', display, true_scroll)

    # destruction particles
    destruction_particles.update(level_map)
    destruction_particles.render(display, true_scroll)

    # gold
    remove_list = []
    n = 0
    for gold_particle in gold_particles:
        if gold_particle[3] < 60:
            gold_particle[0] += gold_particle[2][0]*(1-gold_particle[3]/60)
            gold_particle[1] += gold_particle[2][1]*(1-gold_particle[3]/60)
            gold_particle[2][1] += 0.3
        else:
            dif_x = 50-gold_particle[0]
            dif_y = 25-gold_particle[1]
            gold_particle[0] += dif_x/(abs(dif_x)+abs(dif_y))*4*((gold_particle[3]-60)/40)
            gold_particle[1] += dif_y/(abs(dif_x)+abs(dif_y))*4*((gold_particle[3]-60)/40)
            if abs(dif_x) + abs(dif_y) <= 6:
                remove_list.append(n)
        gold_particle[3] += 3
        if gold_particle[3] > 140:
            gold_particle[3] = 140
        display.blit(gold_img,(gold_particle[0],gold_particle[1]))
        n += 1
    remove_list.sort(reverse=True)
    for gold_particle in remove_list:
        gold_s.play()
        gold_particles.pop(gold_particle)
        gold += 1

    # weapons stuff

    weapon.rotation = math.degrees(angle)
    weapon.aim_dis = aim_dis
    projectile_render_pos = player.get_center()[0]+28*player_direction, player.get_center()[1]

    # print(player.visible)

    if player_state["reload"]:
        weapon.reload(particles_adv, player, player_pos, player_direction, level_map, particle_images, global_time)

    for control in weapon.controls:
        if mouse_state[control]:
            weapon.attack(projectiles, vfx, list(projectile_render_pos), player_pos, level_map, gun_config, player, player_direction, particles_adv, particle_images, global_time)

    for i, entity in itr(entities):
        for i, j in itr(entity):
            if j.visible:
                j.change_frame(1)
                alive = j.display(display, scroll)
            if not alive:
                bar_height = 110
                screen_shake = 20
                style_meter.add_style(100)
                entity.pop(i)
                if tutorial == 1:
                    tutorial = 0

    weapon.render(display, ((player.get_center()[0]+12*player_direction)-scroll[0], player.get_center()[1]+5-scroll[1]))
    player.visible = True

    # particle rendering

    for particle in leaves.copy():
        alive = particle.update(0.1)
        shift = math.sin(particle.x / 20 + global_time / 40) * 16
        particle.draw(display, (scroll[0] + shift, scroll[1]))
        if not alive:
            leaves.remove(particle)

    for fly_obj in soul_flies:
        fly = fly_obj.data
        fly[0][0] += math.cos(fly[1]) * fly[3]
        fly[0][1] += math.sin(fly[1]) * fly[3]
        fly[1] += fly[2]
        if random.random() < 0.01:
            # fly[2] += random.random() * 0.01
            fly[2] = random.random() * 0.2 - 0.1
        render_pos = (int(fly[0][0] - scroll[0] * 1.5) % 600, int(fly[0][1] - scroll[1] * 1.5) % 400)
        display.set_at(render_pos, (109, 202, 232))
        glow(light_surf, fly_obj, render_pos, 5, blue=True)
        glow(light_surf, fly_obj, render_pos, 18, blue=True)

    glow(light_surf, player, window_offset, 600)

    # lighting
    display.blit(light_surf, (0, 0), special_flags=BLEND_RGBA_MULT)

    # minimap
    Minimap.update()
    dark_surf = pygame.Surface(Minimap.size)
    dark_surf.fill((30, 30, 30))
    display.blit(dark_surf, (display.get_width() - (misc['map_ui'].get_width() - 1), 5), special_flags=pygame.BLEND_RGBA_ADD)
    display.blit(Minimap.map_surf, (display.get_width() - (misc['map_ui'].get_width() - 1), 5), special_flags=pygame.BLEND_RGBA_ADD)
    display.blit(misc['map_ui'], (display.get_width() - (misc['map_ui'].get_width() + 5), -1))

    # visual effects
    vfx.update()
    vfx.render_back(display, true_scroll)
    vfx.render_front(display, true_scroll)

    # tutorial ui
    if tutorial == 2:
        display.blit(tutorial_img, (player.get_center()[0] - 20 - scroll[0], player.get_center()[1] - scroll[1] - 52 + (global_time % 60 // 40)))
    elif tutorial == 1 or tutorial_x < display.get_width() + 100:
        if tutorial == 1:
            tutorial_x += (display.get_width() // 2 - 100 - tutorial_x) / 20
        elif tutorial == 0:
            tutorial_x += (display.get_width() + 150 - tutorial_x) / 20
        l_pos = (tutorial_x, display.get_height() // 2 - 8 + (global_time % 60) // 40)
        large_font.render(display, "prevent the demonic invasion", l_pos)
    if title_notice:
        title_notice -=  0.008
        title_notice = max(0, title_notice)
        w = title.get_width()
        l = title.get_height() // 2
        if title_notice > 0.8:
            l_pos = (display.get_width() // 2 - w // 2, display.get_height() // 2 - l - display.get_height() // 2 * (title_notice - 0.8) * 10)
        elif title_notice < 0.2:
            l_pos = (display.get_width() // 2 - w // 2, display.get_height() // 2 - l + (display.get_height() // 2 + 20) * (0.2 - title_notice) * 10)
        else:
            l_pos = (display.get_width() // 2 - w // 2, display.get_height() // 2 - l)
            # time.sleep(0.05)
        display.blit(title, l_pos)



    # weapon ui
    small_font.render(display, str(weapon.ammo) + '/' + str(ammo[weapon.ammo_type]), (5, 25))

    # weapons
    player_items = get_items(inventory, 'active')
    weapon_masks = [pygame.mask.from_surface(weapon.directory) for weapon in get_items(inventory, 'active')]
    offset = 0
    base_pos = 35
    for i, mask in enumerate(weapon_masks):
        color = (139, 171, 191, 255)
        if player_items[i] == weapon:
            color = (255, 255, 255, 255)
        weapon_img = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        weapon_img = pygame.transform.scale(weapon_img, (weapon_img.get_width() // 2, weapon_img.get_height() // 2))
        if player_items[i] == weapon:
            pygame.draw.line(display, (255, 255, 255), (3, base_pos + offset), (3, base_pos + offset + weapon_img.get_height()))
        display.blit(weapon_img, (5 - mask.get_bounding_rects()[0].left, base_pos + offset))
        offset += weapon_img.get_height() + 2

    # health
    pygame.draw.rect(display, (189, 31, 63), pygame.Rect(6, 6, int((player.health / player_max_health)* 70), 8))
    display.blit(misc['health_ui'], (5, 5))

    display.blit(misc['cursor'], (mouse_pos[0] - window_offset[0] - misc['cursor'].get_width() // 2, mouse_pos[1] - window_offset[1] - misc['cursor'].get_height() // 2))
    
    # skills
    for i in range(4):
        skill_count = 4
        pos = display.get_height() - skills_images['dash'].get_height() - ((5 * i) + skills_images['dash'].get_height() * i) - 8
        # if i == 0:
        if skills[i]:
            skills[i].render(skills_images, (5, pos))
        # display.blit(misc["skill"], (pos, display.get_height() - 22 - 19))
    # for i in range(3):
    #     if skills[i]:
    #         skills[i].render(skills_images, (5, display.get_height() - skills_images['test_0'].get_height()) - 10)
    # display.blit(skills_images['test_2'], (5, (display.get_height() - skills_images['test_2'].get_height()) - (20 + skills_images['test_0'].get_height() * 2)))
    # display.blit(skills_images['test_1'], (5, (display.get_height() - skills_images['test_1'].get_height()) - (15 + skills_images['test_0'].get_height())))
    # display.blit(skills_images['test_0'], (5, (display.get_height() - skills_images['test_0'].get_height()) - 10))
    for i in range(4):
        y_pos = display.get_height() - skills_images['dash'].get_height() - ((5 * i) + skills_images['dash'].get_height() * i) + 7
        if skills[i]:
            for j in range(int(skills[i].charges)):
                x_pos = 5 + misc['charge'].get_width() * j
                display.blit(misc['charge'], (x_pos, y_pos))

    display.blit(gold_img, (50, 25))
    small_font.render(display, str(gold), (55, 25))

    if win != 0:
        win += 1

    game_speed += (1 - game_speed) / 20
    if win < 90:
        bar_height += ((1 - game_speed) * 40 - bar_height) / 10
    elif win >= 90:
        bar_height += (210 - bar_height) / 5
        if bar_height > 110:
            win = 0

    if abs(1 - game_speed) < 0.05:
        game_speed = 1

    # if win == 0:
    #     win = 1

    # Bars --------------------------------------------------- #
    bar_surf = pygame.Surface((display.get_width(), bar_height))
    bar_surf.fill((8, 5, 8))
    display.blit(bar_surf, (0, 0))
    display.blit(bar_surf, (0, display.get_height() - int(bar_height)))

    if win == 0:
        screen.blit(pygame.transform.scale(display, (900 + int(bar_height * 3), 600 + int(bar_height * 3))), (-6 - int(bar_height * 1.5), -6 - int(bar_height * 1.5)))
    else:
        screen.blit(pygame.transform.scale(display, (900, 600)), (-6, -6))

    # freeze frames
    # delete_list = []

    # if freeze_frame != {}:
    #     slowest_freeze = min(list(freeze_frame))
    #     if freeze_frame[slowest_freeze] > dt:
    #         dt *= slowest_freeze * 5
    #     else:
    #         dt -= freeze_frame[slowest_freeze] * (1 - slowest_freeze)
    
    # for freeze_amount in freeze_frame:
    #     if freeze_frame[freeze_amount] > dt:
    #         freeze_frame[freeze_amount] -= dt
    #     else:
    #         freeze_frame[freeze_amount] = 0
    #         delete_list.append(freeze_amount)

    # for freeze in delete_list:
    #     del freeze_frame[freeze]

    style_meter.update(display)

    screen.blit(pygame.transform.scale(display,WINDOW_SIZE), screen_render_offset)
    pygame.display.update()
    clock.tick(200)
    print(int(clock.get_fps()))
