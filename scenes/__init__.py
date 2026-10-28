"""Scene registry (ordered back-to-front)."""
from .s01_bag import S1
from .s02_card import S2

SCENES = [S1(), S2()]
