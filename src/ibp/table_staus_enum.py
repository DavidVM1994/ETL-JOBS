from enum import IntEnum

class ControlTableAllowedStates(IntEnum):
    READY=0
    LOADING=1
    IMPORT=2
    SUCCESS=3
    FREEZE=4