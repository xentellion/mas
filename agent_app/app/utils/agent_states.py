from enum import Enum, auto, IntEnum


class State(Enum):
    IDLE = auto()
    WALKING = auto()
    PERFORMING = auto()
    REQUESTING = auto()
    BOARDING = auto()
    COMPLETE = auto()


class GateTransition(IntEnum):
    Any = 0
    InOnly = 1
    OutOnly = 2


class GateAllowedSize(IntEnum):
    OnlySmall = 1
    Any = 2
    OnlyBig = 3
