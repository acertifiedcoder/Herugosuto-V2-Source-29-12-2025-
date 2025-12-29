class Item:
    def __init__(self, directory, owner_ammo, type, config, entities, owner, amount=1):
        self.directory = pygame.image.load(directory).convert_alpha()
        self.type = type
        self.amount = amount
        self.entities = entities
        self.config = config
        self.owner_ammo = owner_ammo
        self.owner = owner