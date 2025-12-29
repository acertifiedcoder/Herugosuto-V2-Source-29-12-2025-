import pygame
pygame.init()

from data.core_funcs import *
from data.bezier import generate_line_chain_vfx

# from data.text import *

def render_item_popup_name(surf, bezier, time, item_name, text):
    text_offset = 8 - bezier.calculate_x(time) * 8
    new_item_name = ' '
    for i, char in enumerate(item_name.replace('_', ' ')):
        if i == 0:
            new_item_name += char.upper()
        elif item_name[i - 1] == ' ':
            new_item_name += char.upper()
        else:
            new_item_name += char
    text_surf = pygame.Surface((text.width(item_name)+1, 8))
    text_surf.set_colorkey((0, 0, 0))
    text.render(text_surf, new_item_name, [0, text_offset])
    return text_surf

class ToolTips:
    def __init__(self):
        self.tooltips = []

    def update(self, dt):
        for i, tooltip in itr(self.tooltips):
            tooltip[2].update(dt * tooltip[1])
            if tooltip[2].time < 0:
                self.tooltips.pop(i)

    def render(self, surf, pos, font):
        for tooltip in self.tooltips:
            tooltip[2].draw(surf, offset=pos)
            for tooltip in self.tooltips:
                if tooltip[0] == "item":
                    surf.blit(render_item_popup_name(surf, tooltip[2].bezier, tooltip[2].time, tooltip[3].type, font), (tooltip[2].base_offset[0] - pos[0] + 5, tooltip[2].base_offset[1] - pos[1] - 12))

    def add_tooltip(self, text, location, assosciated_entity):
        self.tooltips.append([text, 1, generate_line_chain_vfx('found_item', 'bounce_out', list(location)), assosciated_entity])
        # print(text)
        return self.tooltips[-1]