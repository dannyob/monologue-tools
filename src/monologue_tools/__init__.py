"""Monologue Tools - Personal diary and newsletter management tools."""

__version__ = "0.1.0"
__author__ = "Danny O'Brien"
__email__ = "danny@spesh.com"

from .notion2monologue import main as notion2monologue_main
from .transformnotion import main as transformnotion_main

__all__ = ["notion2monologue_main", "transformnotion_main"]
