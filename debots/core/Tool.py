from .Entity import Entity
from abc import ABC, abstractmethod
from .Message import Message
from debots.message_colors import *

class Tool(Entity, ABC):

    def __init__(self, name, desc, examples, color):
        super().__init__(name, desc, color)
        self.examples = examples

    @abstractmethod
    def call(self, message: Message) -> Message:
        pass

class FunctionTool(Tool):

    def __init__(self, f, name, desc, examples, color):
        super().__init__(name, desc, examples, color)
        examples:  str
        self.f = f

    def call(self, message: Message) -> Message:
        assert message.receiver == self
        return Message(self, message.sender, self.f(message.content))

