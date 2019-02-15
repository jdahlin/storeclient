import enum
from typing import List


class RiskType(enum.Enum):
    beta = 'beta'
    candidate = 'candidate'
    edge = 'edge'
    stable = 'stable'

    @classmethod
    def all_strings(cls) -> List[str]:
        return list(map(str, cls.__members__.values()))


class MediaType(enum.Enum):
    icon = 'icon'
    banner = 'banner'
    banner_icon = 'banner_icon'
    screenshot = 'screenshot'
