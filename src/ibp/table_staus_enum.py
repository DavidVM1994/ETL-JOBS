from enum import IntEnum

class ControlTableStates(IntEnum):
    READY=0
    LOADING=1
    IMPORT=2
    SUCCESS=3
    FREEZE=4