class Item:
    def __init__(self, game, owner, type, amount=1):
        self.game = game
        self.type = type
        self.amount = amount
        self.owner = owner