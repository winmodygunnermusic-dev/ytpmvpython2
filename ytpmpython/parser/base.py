"""
Abstract parser base and registry.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional
from ..events import Event
import logging

logger = logging.getLogger(__name__)
_PARSERS: Dict[str, Callable[[], "BaseParser"]] = {}

def register_parser(name: str):
    def deco(cls):
        _PARSERS[name.lower()] = cls
        logger.debug("Parser registered: %s -> %s", name, cls)
        return cls
    return deco

def get_parser_for_format(name: str) -> Optional["BaseParser"]:
    factory = _PARSERS.get(name.lower())
    if factory:
        return factory()
    return None

class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: str) -> List[Event]:
        """
        Parse the file at path and return a timeline list of Event objects.
        Implementations should be robust to large inputs.
        """
        raise NotImplementedError