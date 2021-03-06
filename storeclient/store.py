import datetime
import hashlib
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from storeclient.client import Client
from storeclient.dateutils import parse_datetime
from storeclient.snap import Snap


def parse_url_query(url: str) -> Dict[str, str]:
    parts = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parts.query))


@dataclass
class SearchInfo:
    aliases: List[Optional[str]]
    anon_download_url: Optional[str]
    apps: List[Optional[str]]
    architecture: Optional[List[str]]
    binary_filesize: int
    channel: Optional[str]
    common_ids: Optional[List[str]]  # ?
    confinement: Optional[str]  # strict | classic ?
    contact: Optional[str]
    content: Optional[str]
    date_published: datetime.datetime
    deltas: Optional[List[str]]  # ?
    description: Optional[str]
    developer_id: Optional[str]
    developer_name: Optional[str]
    developer_validation: Optional[str]
    download_sha3_384: Optional[str]
    download_sha512: Optional[str]
    download_url: Optional[str]
    gated_snap_ids: List[str]  # ?
    icon_url: Optional[str]
    last_updated: datetime.datetime
    license: Optional[str]
    name: Optional[str]
    origin: Optional[str]
    package_name: Optional[str]
    prices: Dict[str, str]  # ?
    private: bool
    publisher: Optional[str]
    ratings_average: Optional[str]
    release: Optional[List[str]]
    revision: int
    screenshot_urls: Optional[List[str]]
    snap_id: Optional[str]
    summary: Optional[str]
    support_url: Optional[str]
    title: Optional[str]
    version: Optional[str]
    website: Optional[str]

    def __hash__(self):
        return hash(self.snap_id)

    def __repr__(self):
        return f'<{type(self).__name__} {self.package_name} {self.revision}>'

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        return cls(
            aliases=data.get('aliases'),
            anon_download_url=data.get('anon_download_url'),
            apps=data.get('apps'),
            architecture=data.get('architecture'),
            binary_filesize=data.get('binary_filesize'),
            channel=data.get('channel'),
            common_ids=data.get('common_ids'),
            confinement=data.get('confinement'),
            contact=data.get('contact'),
            content=data.get('content'),
            date_published=parse_datetime(data.get('date_published')),
            deltas=data.get('deltas'),
            description=data.get('description'),
            developer_id=data.get('developer_id'),
            developer_name=data.get('developer_name'),
            developer_validation=data.get('developer_validation'),
            download_sha3_384=data.get('download_sha3_384'),
            download_sha512=data.get('download_sha512'),
            download_url=data.get('download_url'),
            gated_snap_ids=data.get('gated_snap_ids'),
            icon_url=data.get('icon_url'),
            last_updated=data.get('last_updated'),
            license=data.get('license'),
            name=data.get('name'),
            origin=data.get('origin'),
            package_name=data.get('package_name'),
            prices=data.get('prices'),
            private=data.get('private'),
            publisher=data.get('publisher'),
            ratings_average=data.get('ratings_average'),
            release=data.get('release'),
            revision=data.get('revision'),
            screenshot_urls=data.get('screenshot_urls'),
            snap_id=data.get('snap_id'),
            summary=data.get('summary'),
            support_url=data.get('support_url'),
            title=data.get('title'),
            version=data.get('version'),
            website=data.get('website'),
        )

    def download(self, filename=None):
        if filename is None:
            filename = self.download_url.split('/')[-1]

        r = requests.get(self.download_url, stream=True)
        sha = hashlib.sha3_384()
        BLOCKSIZE = 16 * 1024
        with open(filename, 'wb') as f:
            file_buffer = r.raw.read(BLOCKSIZE)
            f.write(file_buffer)
            while len(file_buffer) > 0:
                file_buffer = r.raw.read(BLOCKSIZE)
                f.write(file_buffer)
                sha.update(file_buffer)
        if sha.hexdigest() != self.download_sha3_384:
            raise ValueError("Hash failed")


class Store:

    def __init__(self, client: Optional[Client] = None) -> None:
        self.client = client or Client.get_default()

    def snap(self, name: str) -> Snap:
        """Get info from the snap and its released revisions."""
        r = self.client.snap_info(name)
        r.raise_for_status()

        data: Dict[str, Any] = r.json()
        return Snap(
            _client=self.client,
            _data=data,
            name=name,
            id=data['snap-id'],
        )

    def snaps(self) -> List[SearchInfo]:
        return self.search()

    def search(self,
               text: Optional[str]=None,
               fields: Optional[List[str]]=None) -> List[SearchInfo]:
        page = None
        while True:
            r = self.client.search(
                text=text,
                fields=fields,
                page=page,
                page_size=100)
            data = r.json()
            for row in data['_embedded']['clickindex:package']:
                yield SearchInfo.from_json(row)
            next = data['_links'].get('next')
            if next is None:
                break
            query = parse_url_query(next['href'])
            page = int(query['page'])
