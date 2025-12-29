import os
from scripts.weapon import Weapon

WEAPONS = {}

for script in os.listdir('scripts/weapon_objs'):
    if script not in ['__pycache__']:
        script_name = script[:-3]
        class_name = script_name[0].upper() + script_name[1:] + 'Weapon'
        m = __import__('scripts.weapon_objs.' + script_name, fromlist=[class_name])
        WEAPONS[script_name] = getattr(m, class_name)

def create_weapon(game, owner, weapon_type):
    if weapon_type in WEAPONS:
        return WEAPONS[weapon_type](game, owner, weapon_type)
    else:
        return Weapon(game, owner, weapon_type)