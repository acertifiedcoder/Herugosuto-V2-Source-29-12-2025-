import pygame, math, os

global e_colorkey
e_colorkey = (0, 0, 0)

def read_f(path):
    f = open(path, 'r')
    dat = f.read()
    f.close()
    return dat

def write_f(path, dat):
    f = open(path, 'w')
    f.write(dat)
    f.close()

def swap_color(img,old_c,new_c):
    global e_colorkey
    img.set_colorkey(old_c)
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img,(0,0))
    return surf

def clip(surf,x,y,x_size,y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x,y,x_size,y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()

def rect_corners(points):
    point_1 = points[0]
    point_2 = points[1]
    out_1 = [min(point_1[0], point_2[0]), min(point_1[1], point_2[1])]
    out_2 = [max(point_1[0], point_2[0]), max(point_1[1], point_2[1])]
    return [out_1, out_2]

def corner_rect(points):
    points = rect_corners(points)
    r = pygame.Rect(points[0][0], points[0][1], points[1][0] - points[0][0], points[1][1] - points[0][1])
    return r

def points_between_2d(points):
    points = rect_corners(points)
    width = points[1][0] - points[0][0] + 1
    height = points[1][1] - points[0][1] + 1
    point_list = []
    for y in range(height):
        for x in range(width):
            point_list.append([points[0][0] + x, points[0][1] + y])
    return point_list

def angle_to(points):
    return math.atan2(points[1][1] - points[0][1], points[1][0] - points[0][0])

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

def load_img(path, colorkey=(255, 255, 255)):
    img = pygame.image.load(path).convert()
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

def advance(pos, angle, amt):
    pos[0] += math.cos(angle) * amt
    pos[1] += math.sin(angle) * amt
    return pos

def to_cart(angle, dis):
    return [math.cos(angle) * dis, math.sin(angle) * dis]

def to_polar(vector):
    return [math.atan2(*(vector[::-1])), get_dis([0, 0], vector)]

def get_dis(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def blit_center(target_surf, surf, loc):
    target_surf.blit(surf, (loc[0] - surf.get_width() // 2, loc[1] - surf.get_height() // 2))

def blit_center_add(target_surf, surf, loc):
    target_surf.blit(surf, (loc[0] - surf.get_width() // 2, loc[1] - surf.get_height() // 2), special_flags=pygame.BLEND_RGBA_ADD)

