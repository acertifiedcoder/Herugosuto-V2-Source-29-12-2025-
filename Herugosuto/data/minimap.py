import pygame
import math

CHUNK_SIZE = 4
CHUNK_PIXELS = CHUNK_SIZE * 16
TILE_SIZE = 16

# def get_tile(pos, map, target_layer=None):
#     pos = tuple(pos)
#     if pos in map:
#         if target_layer:
#             if target_layer in map[pos]:
#                 return map[pos][target_layer]
#             else:
#                 return None
#         else:
#             return map
#     else:
#         return None

class Minimap:
    def __init__(self, pos, map):
        self.pos = pos
        self.map = map
        self.minimap_data = {}
        self.size = (60, 45)
        self.map_surf = pygame.Surface(self.size)

    def update_map_surf(self, chunk_pos):
        base_pos = [chunk_pos[0] * CHUNK_SIZE, chunk_pos[1] * CHUNK_SIZE]
        surf = pygame.Surface((CHUNK_SIZE, CHUNK_SIZE))
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                if self.map.get_tile((base_pos[0] + x, base_pos[1] + y)):
                    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    for d in directions:
                        if not self.map.get_tile((base_pos[0] + x + d[0], base_pos[1] + y + d[1])):
                            surf.set_at((x, y), (80, 90, 100))
        self.minimap_data[chunk_pos] = surf

    def update(self):
        self.map_surf = pygame.Surface(self.size)
        pos = self.pos
        display_size = [1200,800]
        chunk_pos = (int(pos[0] // CHUNK_PIXELS), int(pos[1] // CHUNK_PIXELS))
        offset = [(self.size[0] * TILE_SIZE - display_size[0]) / 2, (self.size[1] * TILE_SIZE - display_size[1]) / 2]
        render_base_pos = (int((pos[0] - offset[0]) // CHUNK_PIXELS), int((pos[1] - offset[1]) // CHUNK_PIXELS))
        for y in range(display_size[1] // CHUNK_PIXELS + 1):
            for x in range(display_size[0] // CHUNK_PIXELS + 1):
                target_pos = (x + chunk_pos[0], y + chunk_pos[1])
                if target_pos not in self.minimap_data:
                    self.update_map_surf(target_pos)
        for y in range(self.size[1]):
            for x in range(self.size[0]):
                target_pos = (x + render_base_pos[0], y + render_base_pos[1])
                if target_pos in self.minimap_data:
                    self.map_surf.blit(self.minimap_data[target_pos], (render_base_pos[0] * CHUNK_SIZE - (pos[0] - offset[0]) // TILE_SIZE + x * CHUNK_SIZE, render_base_pos[1] * CHUNK_SIZE - (pos[1] - offset[1]) // TILE_SIZE + y * CHUNK_SIZE))
        self.map_surf.set_colorkey((0, 0, 0))