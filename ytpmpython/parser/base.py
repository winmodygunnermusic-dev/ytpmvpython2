"""
Parser base classes and plugin registry.

Parsers should subclass BaseParser and implement parse(path)->List[Event].
They should register themselves using the @register_parser(format_name) decorator.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional
from ..events import Event
import logging

logger = logging.getLogger(__name__)

# Plugin registry mapping format name -> parser factory
_PARSER_REGISTRY: Dict[str, Callable[[], "BaseParser"]] = {}


def register_parser(format_name: str):
    """
    Decorator to register a parser class for a format name.

    Example:
        @register_parser("midi")
        class MidiParser(BaseParser):
            ...
    """
    def decorator(cls):
        _PARSER_REGISTRY[format_name.lower()] = cls
        logger.debug("Registered parser %s for format '%s'", cls, format_name)
        return cls
    return decorator


def get_parser_for_format(format_name: str) -> Optional["BaseParser"]:
    """Return a parser instance for the named format, or None."""
    factory = _PARSER_REGISTRY.get(format_name.lower())
    if factory:
        return factory()
    return None


class BaseParser(ABC):
    """Abstract base class for timeline parsers."""

    @abstractmethod
    def parse(self, path: str) -> List[Event]:
        """
        Parse the file at path and return a list of Event objects.

        Implementations should be memory-efficient where possible (streaming).
        """
        raise NotImplementedError