from .Entity import Entity

new_messages_verbal = False

def set_new_messages_verbal(verbal):
    global new_messages_verbal
    new_messages_verbal = verbal

def colorize(text: str, color_code: int) -> str:
    """给文本添加 ANSI 颜色代码"""
    return f"\033[38;5;{color_code}m{text}\033[0m"

class Message:
    sender: Entity
    receiver: Entity
    content: str

    def __init__(self, sender, receiver, content):
        assert isinstance(sender, Entity)
        assert isinstance(receiver, Entity)
        assert isinstance(content, str)
        self.sender = sender
        self.receiver = receiver
        self.content = content
        global new_messages_verbal
        if new_messages_verbal:
            self.print()

    def print(self, message_printer=print):
        sender_name_colored = colorize(self.sender.name, self.sender.color)
        receiver_name_colored = colorize(self.receiver.name, self.receiver.color)
        message_printer(f"{sender_name_colored} -> {receiver_name_colored}: {self.content}")