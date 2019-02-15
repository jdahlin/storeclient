import datetime
import hashlib
import json
import mimetypes
import pprint
import os
import sys
from functools import lru_cache
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from pymacaroons import Macaroon
from requests import Response, Session, HTTPError

from storeclient.enums import MediaType

HttpKey = Union[bytes, str]
HttpValue = Union[bytes, str, int]
HttpData = Union[Dict[HttpKey, HttpValue],
                 List[Tuple[HttpKey, HttpValue]]]
ALL_PERMISSIONS = [
    'edit_account',
    'modify_account_key',
    'package_access',
    'package_manage',
    'package_metrics',
    'package_push',
    'package_purchase',
    'package_register',
    'package_release',
    'package_update',
    'package_upload',
    'package_upload_request',
    'store_admin',
    'store_review',
]
CONSTANTS = {
    'local': {
        'sso_location': os.environ.get(
            'SSO_LOCATION',
            'login.staging.ubuntu.com'),
        'sso_base_url': os.environ.get(
            'SSO_BASE_URL',
            'https://login.staging.ubuntu.com'),
        'sca_base_url': os.environ.get(
            'SCA_BASE_URL',
            'http://0.0.0.0:8000'),
        'api_base_url': os.environ.get(
            'API_BASE_URL',
            'http://0.0.0.0:8000'),
    },
    'staging': {
        'sso_location': 'login.staging.ubuntu.com',
        'sso_base_url': 'https://login.staging.ubuntu.com',
        'sca_base_url': os.environ.get(
            'SCA_ROOT_URL', 'https://dashboard.staging.snapcraft.io'),
        'api_base_url': os.environ.get(
            'API_ROOT_URL', 'https://api.staging.snapcraft.io'),

    },
    'production': {
        'sso_location': 'login.ubuntu.com',
        'sso_base_url': 'https://login.ubuntu.com',
        'sca_base_url': 'https://dashboard.snapcraft.io',
        'api_base_url': 'https://api.snapcraft.io',
    },
}
DEFAULT_HEADERS = {
    'User-Agent': 'storeclient/{}'.format(
        os.environ.get('SNAP_VERSION', 'devel')),
    'Accept': 'application/json, application/hal+json',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
}


def get_store_authorization(
        session: Session,
        email: str,
        password: str,
        environment: str,
        permissions: Optional[List[str]] = None,
        channels: Optional[List[str]] = None):
    """Return the serialised root and discharge macaroon.

    Get a permissions macaroon from SCA and discharge it in SSO.
    """
    headers = DEFAULT_HEADERS.copy()
    # Request a SCA root macaroon with hard expiration in 180 days.
    sca_data = {
        'permissions': permissions or ['package_access'],
        'expires': (
                datetime.date.today() + datetime.timedelta(days=180)
        ).strftime('%Y-%m-%d 00:00:00')
    }
    if channels:
        sca_data.update({
            'channels': channels
        })
    response = session.request(
        url='{}/dev/api/acl/'.format(CONSTANTS[environment]['sca_base_url']),
        method='POST', json=sca_data, headers=headers)
    root = response.json()['macaroon']

    caveat, = [
        c for c in Macaroon.deserialize(root).third_party_caveats()
        if c.location == CONSTANTS[environment]['sso_location']
    ]
    # Request a SSO discharge macaroon.
    sso_data = {
        'email': email,
        'password': password,
        'caveat_id': caveat.caveat_id,
    }
    response = session.request(
        url='{}/api/v2/tokens/discharge'.format(
            CONSTANTS[environment]['sso_base_url']),
        method='POST', json=sso_data, headers=headers)
    # OTP/2FA is optional.
    if (response.status_code == 401 and
            response.json().get('code') == 'TWOFACTOR_REQUIRED'):
        sys.stderr.write('Second-factor auth for {}: '.format(environment))
        sso_data.update({'otp': input()})
        response = session.request(
            url='{}/api/v2/tokens/discharge'.format(
                CONSTANTS[environment]['sso_base_url']),
            method='POST', json=sso_data, headers=headers)
    discharge = response.json()['discharge_macaroon']
    return root, discharge


def get_authorization_header(root: str, discharge: str) -> str:
    """Bind root and discharge returning the authorization header."""
    bound = Macaroon.deserialize(root).prepare_for_request(
        Macaroon.deserialize(discharge))
    return 'Macaroon root={}, discharge={}'.format(root, bound.serialize())


class Client:
    def __init__(self, *,
                 email: Optional[str] = None,
                 password: Optional[str] = None,
                 environment: Optional[str] = 'production') -> None:
        self.session = Session()
        self.email = email
        self.password = password
        self.environment = environment
        self.channels = []
        self.permissions = ALL_PERMISSIONS

    def _fetch_authorization_header(self):
        root, discharge = get_store_authorization(
            session=self.session,
            email=self.email,
            password=self.password,
            permissions=self.permissions,
            channels=self.channels,
            environment=self.environment)
        authorization = get_authorization_header(root, discharge)
        return authorization

    @classmethod
    @lru_cache()
    def get_default(cls) -> 'Client':
        return Client()

    def _request(self,
                 base_url: str,
                 method: str,
                 url: str,
                 *,
                 headers: Optional[Dict[str, str]] = None,
                 data: Optional[HttpData] = None,
                 params: Optional[HttpData] = None,
                 files: Optional[Dict[str, Any]] = None) -> Response:
        # import pprint
        # pprint.pprint(dict(method=method, url=url, headers=headers, data=data, params=params, files=files))
        r = self.session.request(
            data=data,
            files=files,
            headers=headers,
            method=method,
            params=params,
            url=base_url + url,
        )
        # import pprint
        # pprint.pprint(r.json())
        return r

    def _api_request(self, *args, **kwargs) -> Response:
        base_url = CONSTANTS[self.environment]['api_base_url']
        print('BASE URL', base_url)
        return self._request(base_url, *args, **kwargs)

    def _sca_request(self, *args, **kwargs) -> Response:
        base_url = CONSTANTS[self.environment]['sca_base_url']
        return self._request(base_url, *args, **kwargs)

    def snap_info(self, snap_name: str) -> Response:
        return self._api_request(
            'GET', f'/v2/snaps/info/{snap_name}',
            headers={'Snap-Device-Series': '16'})

    def snap_names(self, architecture='amd64') -> Response:
        return self._api_request(
            'GET', f'/api/v1/snaps/names',
            headers={'X-Ubuntu-Series': '16',
                     'X-Ubuntu-Architecture': architecture})

    # FIXME: scope
    # FIXME: arch
    # FIXME: confinement
    # FIXME: promoted
    # FIXME: section
    # FIXME: search_term
    # FIXME: exclude_non_free
    # FIXME: private
    def search(self,
               text: Optional[str] = None,
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
        return self._api_request(
            'GET', f'/api/v1/snaps/search',
            params=params,
            headers={'X-Ubuntu-Series': '16',
                     'X-Ubuntu-Architecture': 'amd64'})

    def _handle_error(self, r):
        try:
            r.raise_for_status()
        except HTTPError:
            try:
                data = r.json()
            except json.JSONDecodeError:
                data = None
            if data is None:
                print(f'ERROR: {r.status_code}: {r.content}')
            else:
                error = data['error_list'][0]
                print(f'ERROR: {r.status_code}: {error["message"]}')
                extra = error.get('extra')
                if extra:
                    pprint.pprint(extra)

    def get_binary_metadata(self, snap_id: str) -> List[Dict[str, str]]:
        headers = DEFAULT_HEADERS.copy()
        headers['Authorization'] = self._fetch_authorization_header()
        r = self._sca_request(
            'GET', f'/dev/api/snaps/{snap_id}/binary-metadata',
            headers=headers,
        )
        return r.json()

    def clear_binary_metadata(self, snap_id):
        headers = {
            'Accept': 'application/json',
            'Authorization': self._fetch_authorization_header(),
            'Content-Type': 'multipart/form-data',
        }

        r = self._sca_request(
            'POST',
            f'/dev/api/snaps/{snap_id}/binary-metadata',
            data={'info': metadata},
            headers=headers,
            files={'icon': open('/dev/null')},
        )
        self._handle_error(r)
        return r

    def append_binary_metadata(self,
                              snap_id: str,
                              media_type: MediaType,
                              file: Union[str, BinaryIO]):
        if isinstance(file, str):
            fp = open(file, 'rb')
            filename = file
        else:
            fp = file
            filename = file.name
        content = fp.read()
        new_hash = str(hashlib.sha256(content).hexdigest())
        fp.seek(0)
        headers = {
            'Accept': 'application/json',
            'Authorization': self._fetch_authorization_header(),
        }
        key = '1'
        mime_type = mimetypes.guess_type(filename)[0]
        metadata = self.get_binary_metadata(snap_id)
        # for item in metadata:
        #     if item['hash'] == new_hash:
        #         raise Exception("Item already exists")
        metadata.append({
            'type': media_type.value,
            'hash': new_hash,
            'key': key,
            'filename': os.path.basename(filename),
        })
        r = self._sca_request(
            'POST',
            f'/dev/api/snaps/{snap_id}/binary-metadata',
            data={'info': json.dumps(metadata)},
            headers=headers,
            files=[(key, (filename, fp, mime_type))],
        )
        self._handle_error(r)

        return r
