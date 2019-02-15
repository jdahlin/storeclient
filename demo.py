import pprint
import sys

from storeclient.client import Client
from storeclient.enums import MediaType
from storeclient.store import Store, SearchInfo


def search():
    store = Store()
    print(store.search('spotify'))


def all_media():
    store = Store()
    with open('media.txt', 'wt') as f:
        info: SearchInfo
        for info in store.search():
            print(info, info.icon_url)
            #snap = store.snap(info.package_name)
            #print(snap.media())
            if info.icon_url:
                f.write(f'icon {info.package_name} {info.icon_url}\n')
            for screenshot in info.screenshot_urls:
                f.write(f'screenshot {info.package_name} {screenshot}\n')


def sizes():
    import os
    from PIL import Image
    files = os.listdir('shots')
    sizes = [Image.open('shots/' + file).size for file in files]
    x = sorted(sizes, key=lambda a: a[0]*a[1])
    import pprint
    pprint.pprint(x[-30:])


def clear_metadata(client, snap_id):
    client.clear_binary_metadata(snap_id)


def view_metadata(client, snap_id):
    pprint.pprint(client.get_binary_metadata(snap_id))


def add_binary_metadata(client, snap_id, media_type, filename):
    client.append_binary_metadata(snap_id, MediaType[media_type], file=filename)

def main():
    client = Client(
        email='XXXX',
        password='xxx',
        environment='staging',
    )

    action = sys.argv[1]
    snap_id = sys.argv[2]
    # snap = Store(client).snap(snap_name)
    # snap_id = '2Bnjq01P1Uij77j3r8JHEMftw2KSPDuB'

    if action == 'clear':
        clear_metadata(client, snap_id=snap_id)
    elif action == 'view':
        view_metadata(client, snap_id=snap_id)
    elif action == 'add':
        add_binary_metadata(
            client,
            snap_id=snap_id,
            media_type=sys.argv[3],
            filename=sys.argv[4],
        )
    else:
        raise SystemExit(f"Invalid action: {action}")

main()
