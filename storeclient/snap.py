from dataclasses import dataclass
from typing import Dict, Any

from storeclient.channels import Channels


@dataclass
class Snap:
    _data: Dict[str, Any]
    name: str
    id: str

    @property
    def channels(self) -> Channels:
        return Channels.from_channel_maps(self._data['channel-map'])
