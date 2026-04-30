from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    WALKING = auto()
    PERFORMING = auto()
    REQUESTING = auto()
    BOARDING = auto()
    COMPLETE = auto()
