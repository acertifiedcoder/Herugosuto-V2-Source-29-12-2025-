from data.engine import entity
from data.core_funcs import normalize

def physical_rect_filter(tiles):
    valid = []
    for tile in tiles:
        for tile_type in tile[0]:
            if tile_type[0] in ["main_tileset"]:
                valid.append(tile[1])
                break
    return valid

class PhysicsEntity(entity):
    def __init__(self, map, *args):
        super().__init__(*args)
        self.velocity = [0, 0]
        self.motion = self.velocity.copy()
        self.velocity_normalization = [350, 350]
        self.default_gravity = 700
        self.allow_movement = True
        self.gravity_on = True
        self.tile_collisions = True

        self.map = map

    def display(self, surf, scroll):
        self.dt = 1 / 60
        r = super().display(surf, scroll)
        # rects = [t[1] for t in self.map.get_nearby_rects(self.get_center())]

        if self.allow_movement: 
            self.velocity[0] = normalize(self.velocity[0], self.velocity_normalization[0] * self.dt)
            self.velocity[1] = normalize(self.velocity[1], self.velocity_normalization[1] * self.dt)
            if self.gravity_on:
                self.velocity[1] = min(500, self.velocity[1] + self.dt * self.default_gravity)

            collisions = self.move((self.motion[0] * self.dt, self.motion[1] * self.dt), physical_rect_filter(self.map.get_nearby_rects(self.get_center())))
            if collisions["bottom"]:
                self.velocity[1] = 0

        self.motion = self.velocity.copy()

        return r