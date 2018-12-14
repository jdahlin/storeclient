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
