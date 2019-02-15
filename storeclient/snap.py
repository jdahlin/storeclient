from dataclasses import dataclass
from typing import Dict, Any

from storeclient.channels import Channels
from storeclient.store import Client


@dataclass
class Snap:
    _client: Client
    _data: Dict[str, Any]
    name: str
    id: str

    def __hash__(self):
        return hash(self.id)

    @property
    def channels(self) -> Channels:
        return Channels.from_channel_maps(self._data['channel-map'])

    def media(self):
        r = self._client.get_binary_metadata(self.id)
        r.raise_for_status()
        return r.json()
