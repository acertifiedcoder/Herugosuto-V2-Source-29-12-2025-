import math
import random

from scripts.config import config
from scripts.core_funcs import itr

class Hitbox:
    def __init__(self, game, hitbox_type, duration=-1, rect=None, tracked=None, owner=None, angle=None):
        self.game = game
        if tracked:
            self.mode = "tracked"
            self.tracked = tracked
        else:
            self.mode = "rect"
            self.rect = rect
        self.duration = duration
        self.hitbox_type = hitbox_type
        self.config = config['hitboxes'][hitbox_type]
        self.owner = owner
        self.angle = angle

    def update(self, dt):
        if self.mode == "tracked":
            tracked_mask, offset = self.tracked.create_mask()
            mask_surf = tracked_mask.to_surface(setcolor=(255, 0, 0, 255), unsetcolor=(1, 255, 0, 255))
            # display.blit(mask_surf, (offset[0] - true_scroll[0], offset[1] - true_scroll[1]))
            
            for entity in self.game.entities:
                if entity != self.owner:
                    mask_surf = entity.mask.to_surface(setcolor=(255, 0, 0, 255), unsetcolor=(1, 255, 0, 255))
                    entity_offset = entity.calculate_render_offset()
                    collision = tracked_mask.overlap(entity.mask, (int(entity.pos[0] - offset[0]), int(entity.pos[1] - offset[1])))
                    # collision_point = (entity.x + collision[0], entity.y + collision[1])
                    if collision:
                        collision_point = [offset[0] + collision[0], offset[1] + collision[1]]
                        if self.angle:
                            self.game.vfx.spawn_vfx('slice', collision_point.copy(), random.random() * math.pi / 4 - math.pi / 8 + self.angle, 20 * random.random() + 40, 1.5, 3, 0.1)
                            entity.velocity[0] += math.cos(self.angle) * 300 * (dt) * self.config['knockback']
                            entity.velocity[1] += math.sin(self.angle) * 300 * (dt) * self.config['knockback']
                            entity.hurt = 1
                            # entity.damage(self.config['power'])
                            # if random.randint(1, 3) == 1:
                                # self.game.add_freeze(0.2, 0.2)
                            for i in range(random.randint(15, 30)):
                                self.game.vfx.spawn_group('arrow_impact_sparks', collision_point.copy(), self.angle + math.pi)
                        return False
                        # display.blit(mask_surf, (entity.x  - true_scroll[0], entity.y - true_scroll[1]))
            return self.tracked.alive
        

class Hitboxes:
    def __init__(self, game):
        self.game = game
        self.hitboxes = []

    def update(self):
        for i, hitbox in itr(self.hitboxes):
            alive = hitbox.update(self.game.dt)
            if not alive:
                self.hitboxes.pop(i)

    def add_hitbox(self, *args, **kwargs):
        self.hitboxes.append(Hitbox(*args, **kwargs))