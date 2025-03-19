from .Tool import Tool
from abc import ABC, abstractmethod

class Toolset(ABC):

    @property
    @abstractmethod
    def tools(self) -> [Tool]:
        pass
