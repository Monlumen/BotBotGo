

class APIKey:

    def __init__(self, name, key):
        self.name = name
        self.key = key

    def get(self):
        if not self.key:
            raise NullAPIKeyException(self.name)
        return self.key

    def set(self, key):
        self.key = key

    def __bool__(self):
        return self.key is not None and self.key != ""


class NullAPIKeyException(Exception):

    def __init__(self, name):
        super().__init__(f"\n模型{name}没有插入 API Key. 你可以: \n1. 使用 debots.set_api_keys() 来设置必要的 OpenAI, OpenRouter, Serper API Key\n2. 或者使用 debots.apply_public_api_keys() 来一键插入公共 API Key")
