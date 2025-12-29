import random
import math

from scripts.weapon import Weapon

class HatchetWeapon(Weapon):
    def attack(self):
        self.invisible = 0.2
        if self.game.player.flip:
            self.game.vfx.spawn_vfx('arc', self.owner.center.copy(), 2, random.random() * 3, math.radians(self.rotation - 20), 6, random.random() * 6 + 100, 0.5, start=0, end=0.5, duration=0.7, arc_stretch=300, motion=random.randint(300, 450), decay=['down', 100], fade=0.5)
        else:
            self.game.vfx.spawn_vfx('arc', self.owner.center.copy(), 2, random.random() * 3, math.radians(self.rotation + 20), 6, random.random() * 6 + 100, 0.5, start=0.5, end=1, duration=0.7, arc_stretch=300, motion=random.randint(300, 450), decay=['up', 100], fade=0.5)
        arc_mask, offset = self.game.vfx.get_last_added().create_mask()
        self.game.hitboxes.add_hitbox(self.game, 'hatchet', tracked=self.game.vfx.get_last_added(), owner=self.owner, angle=math.radians(self.rotation)) 