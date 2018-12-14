from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union

from requests import Response, Session

HttpKey = Union[bytes, str]
HttpValue = Union[bytes, str, int]
HttpData = Union[Dict[HttpKey, HttpValue],
                 List[Tuple[HttpKey, HttpValue]]]


class Client:
    BASE_URL = 'https://api.snapcraft.io'

    def __init__(self) -> None:
        self.session = Session()

    @classmethod
    @lru_cache()
    def get_default(cls) -> 'Client':
        return Client()

    def _request(self,
                 method: str,
                 url: str,
                 *,
                 headers: Dict[str, str] = None,
                 data: HttpData = None,
                 params: HttpData = None) -> Response:
        url = self.BASE_URL + url
        return self.session.request(
            method, url,
            data=data,
            headers=headers,
            params=params)

    def snap_info(self, snap_name: str) -> Response:
        return self._request(
            'GET', f'/v2/snaps/info/{snap_name}',
            headers={'Snap-Device-Series': '16'})

    def snap_names(self, architecture='amd64') -> Response:
        return self._request(
            'GET', f'/api/v1/snaps/names',
            headers={'X-Ubuntu-Series': '16',
                     'X-Ubuntu-Architecture': architecture})

    # FIXME: q
    # FIXME: scope
    # FIXME: arch
    # FIXME: confinement
    # FIXME: promoted
    # FIXME: section
    # FIXME: search_term
    # FIXME: exclude_non_free
    # FIXME: private
    def search(self,
               text: Optional[str]=None,
               *,
               fields: Optional[List[str]] = None,
               page: Optional[int] = None,
               page_size: int = 100) -> Response:
        params: Dict[str, int] = {}
        if text is not None:
            params['q'] = text
        if fields is not None:
            params['fields'] = ','.join(fields)
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['page_size'] = page_size
        return self._request(
            'GET', f'/api/v1/snaps/search',
            params=params,
            headers={'X-Ubuntu-Series': '16',
                     'X-Ubuntu-Architecture': 'amd64'})
