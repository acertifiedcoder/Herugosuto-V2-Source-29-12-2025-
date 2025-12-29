import pygame, math, os, random
from pygame.locals import *
import data.destruction_particles as dp

global e_colorkey
e_colorkey = (0, 0, 0)

def set_global_colorkey(colorkey):
    global e_colorkey
    e_colorkey = colorkey

def clip(surf,x,y,x_size,y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x,y,x_size,y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()

# physics core

# 2d collisions test
def collision_test(object_1,object_list):
    collision_list = []
    for obj in object_list:
        if obj.colliderect(object_1):
            collision_list.append(obj)
    return collision_list

# 2d physics object
class physics_obj(object):

    def __init__(self,x,y,x_size,y_size):
        self.width = x_size
        self.height = y_size
        self.rect = pygame.Rect(x,y,self.width,self.height)
        self.x = x
        self.y = y

    def move(self,movement,platforms,right_ramps=[],left_ramps=[]):
        self.x += movement[0]
        self.rect.x = int(self.x)
        block_hit_list = collision_test(self.rect,platforms)
        collision_types = {'top':False,'bottom':False,'right':False,'left':False,'slant_bottom':False,'data':[]}
        # added collision data to "collision_types". ignore the poorly chosen variable name
        for block in block_hit_list:
            markers = [False,False,False,False]
            if movement[0] > 0:
                self.rect.right = block.left
                collision_types['right'] = True
                markers[0] = True
            elif movement[0] < 0:
                self.rect.left = block.right
                collision_types['left'] = True
                markers[1] = True
            collision_types['data'].append([block,markers])
            self.x = self.rect.x
        self.y += movement[1]
        self.rect.y = int(self.y)
        block_hit_list = collision_test(self.rect,platforms)
        for block in block_hit_list:
            markers = [False,False,False,False]
            if movement[1] > 0:
                self.rect.bottom = block.top
                collision_types['bottom'] = True
                markers[2] = True
            elif movement[1] < 0:
                self.rect.top = block.bottom
                collision_types['top'] = True
                markers[3] = True
            collision_types['data'].append([block,markers])
            self.change_y = 0
            self.y = self.rect.y

        for right_ramp in right_ramps:
            right_hitbox = pygame.Rect(right_ramp.x, right_ramp.y, 16, 16)
            if self.rect.colliderect(right_hitbox): # check if player collided with the bounding box for the ramp
                # get player's position relative to the ramp on the x axis
                rel_x = self.rect.x - right_hitbox.x

                # get height at player's position based on type of ramp
                pos_height = rel_x + self.rect.width # go by player right edge on right ramps
                # is already left edge by default

                # add constraints
                pos_height = min(pos_height, 16)
                pos_height = max(pos_height, 0)

                target_y = right_hitbox.y + 16 - pos_height

                if self.rect.bottom > target_y: # check if the player collided with the actual ramp
                    # adjust player height
                    self.rect.bottom = target_y
                    self.y = self.rect.y

                    collision_types['bottom'] = True

        for left_ramp in left_ramps:
            left_hitbox = pygame.Rect(left_ramp.x, left_ramp.y, 16, 16)
            if self.rect.colliderect(left_hitbox): # check if player collided with the bounding box for the ramp
                # get player's position relative to the ramp on the x axis
                rel_x = self.rect.x - left_hitbox.x

                # get height at player's position based on type of ramp
                pos_height = 16 - rel_x # go by player right edge on right ramps
                # is already left edge by default

                # add constraints
                pos_height = min(pos_height, 16)
                pos_height = max(pos_height, 0)

                target_y = left_hitbox.y + 16 - pos_height

                if self.rect.bottom > target_y: # check if the player collided with the actual ramp
                    # adjust player height
                    self.rect.bottom = target_y
                    self.y = self.rect.y

                    collision_types['bottom'] = True

        return collision_types

# 3d collision detection
# todo: add 3d physics-based movement

class cuboid(object):

    def __init__(self,x,y,z,x_size,y_size,z_size):
        self.x = x
        self.y = y
        self.z = z
        self.x_size = x_size
        self.y_size = y_size
        self.z_size = z_size

    def set_pos(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z

    def collidecuboid(self,cuboid_2):
        cuboid_1_xy = pygame.Rect(self.x,self.y,self.x_size,self.y_size)
        cuboid_1_yz = pygame.Rect(self.y,self.z,self.y_size,self.z_size)
        cuboid_2_xy = pygame.Rect(cuboid_2.x,cuboid_2.y,cuboid_2.x_size,cuboid_2.y_size)
        cuboid_2_yz = pygame.Rect(cuboid_2.y,cuboid_2.z,cuboid_2.y_size,cuboid_2.z_size)
        if (cuboid_1_xy.colliderect(cuboid_2_xy)) and (cuboid_1_yz.colliderect(cuboid_2_yz)):
            return True
        else:
            return False

# entity stuff

def simple_entity(x,y,e_type):
    return entity(x,y,1,1,e_type)

def flip(img,boolean=True):
    return pygame.transform.flip(img,boolean,False)

def blit_center(surf,surf2,pos):
    x = int(surf2.get_width()/2)
    y = int(surf2.get_height()/2)
    surf.blit(surf2,(pos[0]-x,pos[1]-y))

class entity(object):
    global animation_database, animation_higher_database

    def __init__(self,x,y,size_x,size_y,e_type, health=100, alive=True): # x, y, size_x, size_y, type
        self.x = x
        self.y = y
        self.size_x = size_x
        self.size_y = size_y
        self.obj = physics_obj(x,y,size_x,size_y)
        self.animation = None
        self.image = None
        self.animation_frame = 0
        self.animation_tags = []
        self.flip = False
        self.offset = [0,0]
        self.rotation = 0
        self.type = e_type # used to determine animation set among other things
        self.action_timer = 0
        self.action = ''
        self.set_action('idle') # overall action for the entity
        self.entity_data = {}
        self.alpha = None

        self.health = health
        self.alive = alive
        self.visible = True

        self.gen_mask()

    def set_pos(self,x,y):
        self.x = x
        self.y = y
        self.obj.x = x
        self.obj.y = y
        self.obj.rect.x = x
        self.obj.rect.y = y

    def move(self,momentum,platforms,right_ramps=[],left_ramps=[]):
        collisions = self.obj.move(momentum,platforms,right_ramps,left_ramps)
        self.x = self.obj.x
        self.y = self.obj.y
        return collisions

    def damage(self, amount):
        self.health -= amount

    def die(self, entity, image, image_pos, dp, vfx):
        SIZE = 3
        entity_img = image.copy()
        for y in range(entity_img.get_height() // SIZE + 1):
            for x in range(entity_img.get_width() // SIZE + 1):
                img = clip(entity_img, x * SIZE, y * SIZE, SIZE, SIZE)
                if not (img.get_width() * img.get_height()):
                    continue
                angle = math.atan2(y * SIZE + SIZE / 2 - entity_img.get_height() / 2, x * SIZE + SIZE / 2 - entity_img.get_width() / 2)
                dis = math.sqrt((y * SIZE + SIZE / 2 - entity_img.get_height() / 2) ** 2 + (x * SIZE + SIZE / 2 - entity_img.get_width() / 2) ** 2)
                dis /= 8
                dp.add_particle(img, [image_pos[0] + x * SIZE + SIZE // 2, image_pos[1] + y * SIZE + SIZE // 2], [math.cos(angle) * math.sqrt(dis) + random.randint(0, 3) - 1.5, math.sin(angle) * math.sqrt(dis) - 2.5 + random.randint(0, 3) - 1.5, random.randint(0, 180) - 90], duration=random.randint(2,5))
                dp.add_particle(img, [image_pos[0] + x * SIZE + SIZE // 2, image_pos[1] + y * SIZE + SIZE // 2], [math.cos(angle) * math.sqrt(dis) + random.randint(0, 3) - 1.5, math.sin(angle) * math.sqrt(dis) - 2.5 + random.randint(0, 3) - 1.5, random.randint(0, 180) - 90], duration=random.randint(2,5))
        for i in range(16):
            angle = i / 8 * math.pi
            vfx.spawn_vfx('curved_spark', self.get_center().copy(), angle + random.random() / 5, 0, random.random() * 2 + 1, 10, 0.05)
        self.alive = False

    def rect(self):
        return pygame.Rect(self.x,self.y,self.size_x,self.size_y)

    def set_flip(self,boolean):
        self.flip = boolean

    def set_animation_tags(self,tags):
        self.animation_tags = tags

    def set_animation(self,sequence):
        self.animation = sequence
        self.animation_frame = 0

    def set_action(self,action_id,force=False):
        if (self.action == action_id) and (force == False):
            pass
        else:
            self.action = action_id
            anim = animation_higher_database[self.type][action_id]
            self.animation = anim[0]
            self.set_animation_tags(anim[1])
            self.animation_frame = 0

    def get_entity_angle(self,entity_2):
        x1 = self.x+int(self.size_x/2)
        y1 = self.y+int(self.size_y/2)
        x2 = entity_2.x+int(entity_2.size_x/2)
        y2 = entity_2.y+int(entity_2.size_y/2)
        angle = math.atan((y2-y1)/(x2-x1))
        if x2 < x1:
            angle += math.pi
        return angle

    def get_angle_xy(self, target):
        # return math.atan2(entity.y - self.y, entity.x - self.x)
        if isinstance(target, entity):
            return math.atan2(target.get_center()[1] - self.get_center()[1], target.get_center()[0] - self.get_center()[0])
        else:
            return math.atan2(target.y - self.y, target.x - self.x)

    def get_angle_pos(self, target):
        if isinstance(target, entity):
            return math.atan2(target.get_center()[1] - self.get_center()[1], target.get_center()[0] - self.get_center()[0])
        else:
            return math.atan2(target[1] - self.y, target[0] - self.x)
    def get_center(self):
        x = self.x+int(self.size_x/2)
        y = self.y+int(self.size_y/2)
        return [x,y]

    def clear_animation(self):
        self.animation = None

    def set_image(self,image):
        self.image = image

    def set_offset(self,offset):
        self.offset = offset

    def set_frame(self,amount):
        self.animation_frame = amount

    def handle(self):
        self.action_timer += 1
        self.change_frame(1)

    def change_frame(self,amount):
        self.animation_frame += amount
        if self.animation != None:
            while self.animation_frame < 0:
                if 'loop' in self.animation_tags:
                    self.animation_frame += len(self.animation)
                else:
                    self.animation = 0
            while self.animation_frame >= len(self.animation):
                if 'loop' in self.animation_tags:
                    self.animation_frame -= len(self.animation)
                else:
                    self.animation_frame = len(self.animation)-1

    def get_current_img(self):
        if self.animation == None:
            if self.image != None:
                return flip(self.image,self.flip)
            else:
                return None
        else:
            return flip(animation_database[self.animation[self.animation_frame]],self.flip)

    def calculate_render_offset(self, offset=(0, 0)):
        offset = list(offset)
        offset[0] += self.get_current_img().get_width() // 2
        offset[1] += self.get_current_img().get_height() // 2
        return offset

    def get_drawn_img(self):
        image_to_render = None
        if self.animation == None:
            if self.image != None:
                image_to_render = flip(self.image,self.flip).copy()
        else:
            image_to_render = flip(animation_database[self.animation[self.animation_frame]],self.flip).copy()
        if image_to_render != None:
            center_x = image_to_render.get_width()/2
            center_y = image_to_render.get_height()/2
            image_to_render = pygame.transform.rotate(image_to_render,self.rotation)
            if self.alpha != None:
                image_to_render.set_alpha(self.alpha)
            return image_to_render, center_x, center_y

    def gen_mask(self):
        self.mask = pygame.mask.from_surface(self.get_current_img())

    def display(self,surface,scroll):
        self.gen_mask()
        image_to_render = None
        if self.animation == None:
            if self.image != None:
                image_to_render = flip(self.image,self.flip).copy()
        else:
            image_to_render = flip(animation_database[self.animation[self.animation_frame]],self.flip).copy()
        if image_to_render != None:
            center_x = image_to_render.get_width()/2
            center_y = image_to_render.get_height()/2
            image_to_render = pygame.transform.rotate(image_to_render,self.rotation)
            if self.alpha != None:
                image_to_render.set_alpha(self.alpha)
            blit_center(surface,image_to_render,(int(self.x)-scroll[0]+self.offset[0]+center_x,int(self.y)-scroll[1]+self.offset[1]+center_y))
        
        return self.alive

    def get_distance(self, target):
        try:
            return math.sqrt((target.pos[0] - self.x) ** 2 + (target.pos[1] - self.y) ** 2)
        except:
            return math.sqrt((target[0] - self.x) ** 2 + (target[1] - self.y) ** 2)

    def in_range(self, target, range):
        return self.get_distance(target) <= range


# animation stuff

global animation_database
animation_database = {}

global animation_higher_database
animation_higher_database = {}

# a sequence looks like [[0,1],[1,1],[2,1],[3,1],[4,2]]
# the first numbers are the image name(as integer), while the second number shows the duration of it in the sequence
def animation_sequence(sequence,base_path,colorkey=(0, 0, 0),transparency=255):
    global animation_database
    result = []
    for frame in sequence:
        image_id = base_path + base_path.split('/')[-2] + '_' + str(frame[0])
        image = pygame.image.load(image_id + '.png').convert_alpha()
        image.set_colorkey(colorkey)
        image.set_alpha(transparency)
        animation_database[image_id] = image.copy()
        for i in range(frame[1]):
            result.append(image_id)
    return result


def get_frame(ID):
    global animation_database
    return animation_database[ID]

def load_animations(path):
    global animation_higher_database
    f = open(path + 'entity_animations.txt','r')
    data = f.read()
    f.close()
    for animation in data.split('\n'):
        sections = animation.split(' ')
        anim_path = sections[0]
        entity_info = anim_path.split('/')
        entity_type = entity_info[0]
        animation_id = entity_info[1]
        timings = sections[1].split(';')
        tags = sections[2].split(';')
        sequence = []
        n = 0
        for timing in timings:
            sequence.append([n,int(timing)])
            n += 1
        anim = animation_sequence(sequence,path + anim_path)
        if entity_type not in animation_higher_database:
            animation_higher_database[entity_type] = {}
        animation_higher_database[entity_type][animation_id] = [anim.copy(),tags]

# particles

def particle_file_sort(l):
    l2 = []
    for obj in l:
        l2.append(int(obj[:-4]))
    l2.sort()
    l3 = []
    for obj in l2:
        l3.append(str(obj) + '.png')
    return l3

global particle_images
particle_images = {}

def load_particle_images(path):
    global particle_images, e_colorkey
    file_list = os.listdir(path)
    for folder in file_list:
        try:
            img_list = os.listdir(path + '/' + folder)
            img_list = particle_file_sort(img_list)
            images = []
            for img in img_list:
                images.append(pygame.image.load(path + '/' + folder + '/' + img).convert())
            for img in images:
                img.set_colorkey(e_colorkey)
            particle_images[folder] = images.copy()
        except:
            pass

class particle(object):

    def __init__(self,x,y,particle_type,motion,decay_rate,start_frame,custom_color=None):
        self.x = x
        self.y = y
        self.type = particle_type
        self.motion = motion
        self.decay_rate = decay_rate
        self.color = custom_color
        self.frame = start_frame

    def draw(self,surface,scroll):
        global particle_images
        if self.frame > len(particle_images[self.type])-1:
            self.frame = len(particle_images[self.type])-1
        if self.color == None:
            blit_center(surface,particle_images[self.type][int(self.frame)],(self.x-scroll[0],self.y-scroll[1]))
        else:
            blit_center(surface,swap_color(particle_images[self.type][int(self.frame)],(255,255,255),self.color),(self.x-scroll[0],self.y-scroll[1]))

    def update(self):
        self.frame += self.decay_rate
        running = True
        if self.frame > len(particle_images[self.type])-1:
            running = False
        self.x += self.motion[0]
        self.y += self.motion[1]
        return running


# other useful functions

def swap_color(img, old_c, new_c):
    global e_colorkey
    img.set_colorkey(old_c)
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img, (0, 0))
    surf.set_colorkey(e_colorkey)
    return surf

def blit_center(target_surf, surf, loc):
    target_surf.blit(surf, (loc[0] - surf.get_width() // 2, loc[1] - surf.get_height() // 2))
