
from GlobalFunctions import check_os

EMULATOR_DIST_PATH = "dist"

if check_os() == 'Linux':
    EMULATOR_BASE_FILE = "facial_emulator"
elif check_os() == 'Windows':
    EMULATOR_BASE_FILE = "facial_emulator.exe"


DAHUA_CONTROLLER_TYPES = [
    22121, # DHI-ASI7213Y-V3 
    22131
]

HIKVISION_CONTROLLER_TYPES = [
    21101, # 671
    21102  # 673
]


