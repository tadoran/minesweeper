from enum import Enum


class FieldItemState(Enum):
    EMPTY = 0
    MINE = 1
    QUESTIONABLE = 2


class FieldItemVisibility(Enum):
    hidden = 0
    visible = 1


class GameStatus(Enum):
    RUNNING = 0
    LOST = 1
    WON = 2


class GameDifficulty(Enum):
    EASY = (10, 10, 10)
    MEDIUM = (12, 12, 20)
    HARD = (15, 15, 30)
