import datetime
from dataclasses import dataclass
from typing import Dict, Any

from storeclient.enums import RiskType
from storeclient.dateutils import parse_datetime


@dataclass
class Channel:
    name: str
    revision: int
    architecture: str
    risk: RiskType
    created_at: datetime.datetime
    released_at: datetime.datetime
    track: str
    sha3_384: str
    size: int
    url: str
    version: str

    @classmethod
    def from_channel_map(cls, channel_map: Dict[str, Any]) -> 'Channel':
        channel = channel_map['channel']
        download = channel_map['download']
        self = cls(
            architecture=channel['architecture'],
            created_at=parse_datetime(channel_map['created-at']),
            name=channel['name'],
            released_at=parse_datetime(channel['released-at']),
            revision=channel_map['revision'],
            risk=RiskType[channel['risk']],
            sha3_384=download['sha3-384'],
            size=download['size'],
            track=channel['track'],
            url=download['url'],
            version=channel_map['version'],
        )
        return self
