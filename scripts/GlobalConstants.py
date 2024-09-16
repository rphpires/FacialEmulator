
from scripts.GlobalFunctions import check_os

EMULATOR_DIST_PATH = "dist"

if check_os() == 'Linux':
    EMULATOR_BASE_FILE = "facial_emulator_unix"
elif check_os() == 'Windows':
    EMULATOR_BASE_FILE = "facial_emulator_win.exe"


DAHUA_CONTROLLER_TYPES = [
    22111, # DHI-ASI7213X-T1
    22121, # DHI-ASI7213Y-V3 
    22131  # DHI-ASI7214Y-V3
]

HIKVISION_CONTROLLER_TYPES = [
    21101, # DS-K1T671
    21102  # DS-K1T673
]


