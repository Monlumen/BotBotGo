from debots.message_colors import *

class Entity:
    name: str
    desc: str
    examples: str
    color: int

    def __init__(self, name, desc, color=MESSAGE_COLOR_GREEN):
        self.name = name
        self.desc = desc
        self.color = color
