from data.physics_entity import PhysicsEntity
# from data.item import item

class ItemDrop(PhysicsEntity):
    def __init__(self, item_data, *args):
        super().__init__(*args)
        self.item_data = item_data

        self.set_action('idle')
        self.size = [self.size_x, self.size_y]

    