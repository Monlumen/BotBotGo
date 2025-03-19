import debots
from .ParsedPage import ParsedPage
from .parse_history_utils import parse

class ParsedHistory:

    def __init__(self, history = None):
        self.__page_dict = {} # name:str -> page:Page
        if history is not None:
            self.parse(history)

    def add_to_library(self, page: ParsedPage):
        if page.name in self.__page_dict:
            self.__page_dict[page.name].add_lines(page.lines)
        else:
            self.__page_dict[page.name] = page

    def parse(self, history):
        for entry in history:
            parsed_pages = parse(entry["content"])
            for parsed_page in parsed_pages:
                self.add_to_library(parsed_page)

    @property
    def library(self):
        return self.__page_dict.values()