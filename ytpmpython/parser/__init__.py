"""Parser package — register and obtain parsers by format name."""

from .base import register_parser, get_parser_for_format, BaseParser  # re-export
from .midi import MidiParser
from .openmpt import OpenMPTParser

__all__ = ["register_parser", "get_parser_for_format", "BaseParser", "MidiParser", "OpenMPTParser"]