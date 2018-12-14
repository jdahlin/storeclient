import operator
from typing import List, Dict, Any, Iterable, Optional

from storeclient.channel import Channel
from storeclient.enums import RiskType


class Channels:
    def __init__(self, channels: List[Channel]) -> None:
        self._channels = sorted(
            channels, key=operator.attrgetter('released_at'))

    @classmethod
    def from_channel_maps(cls, channel_maps: List[Dict[str, Any]]) -> 'Channels':
        channels = []
        for channel_map in channel_maps:
            channel = Channel.from_channel_map(channel_map)
            channels.append(channel)
        return cls(channels=channels)

    def __repr__(self) -> str:
        return f'<{type(self).__name__}: {len(self)} channels>'

    def __iter__(self) -> Iterable[Channel]:
        return iter(self._channels)

    def find(self, *, risk=None, architecture=None) -> Optional['Channels']:
        if type(risk) == str:
            risk = RiskType[risk]
        results = []
        for channel in self._channels:
            if risk is not None and channel.risk != risk:
                continue
            if architecture is not None and channel.architecture != architecture:
                continue
            results.append(channel)
        if not results:
            return None
        return Channels(results)

    def latest(self) -> Channel:
        return self._channels[-1]
