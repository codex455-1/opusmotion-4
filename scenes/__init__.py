"""Scene registry (ordered back-to-front)."""
from .s01_bag import S1
from .s02_card import S2
from .s03_moscow import S3
from .s04_notes import S4

SCENES = [S1(), S2(), S3(), S4()]
