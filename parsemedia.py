import collections
import csv
import hashlib
import math
import os
import pprint
import urllib.request
from typing import Iterator, NamedTuple
from urllib.parse import quote

from PIL import Image


MEDIA_ROOT = 'https://dashboard.snapcraft.io/site_media/'
DB_QUERY = """SELECT 
p.name, 
m.id, 
m.media_type, 
m.url, 
m.media_name, 
m.media_hash,
m.media_upload
FROM devportal_clickpackagemedia m, devportal_clickpackage p
WHERE p.id = m.application_id;"""


class MediaInfo(NamedTuple):
    snap_name: str
    media_type: str
    filename: str
    format: str
    width: int
    height: int
    aspect_ratio : str
    size: int
    framecount: float
    fps: float
    length: float


def calculate_aspect(width: int, height: int) -> str:
    temp = 0
    x = y = 1
    if width != height:
        if width < height:
            temp = width
            width = height
            height = temp

        divisor = math.gcd(width, height)

        x = int(width / divisor) if not temp else int(height / divisor)
        y = int(height / divisor) if not temp else int(width / divisor)

    return f"{x}:{y}"


def get_avg_fps(img: Image) -> float:
    """ Returns the average framerate of a PIL Image object """
    img.seek(0)
    image_duration = img.info.get('duration')
    if image_duration is None:
        return 0
    frames = duration = 0
    while True:
        try:
            frames += 1
            duration += image_duration
            img.seek(img.tell() + 1)
        except EOFError:
            return frames / duration * 1000


def download(url, local, media_hash):
    urllib.request.urlretrieve(url, local)
    if not media_hash:
        return True
    with open(local, 'rb') as fd:
        file_hash = hashlib.sha256(fd.read()).hexdigest()
        if file_hash == media_hash:
            return True

        print(local, f'differs {file_hash} != {media_hash}')
        return False


def parse_media(rows: Iterator, media_dir: str) -> Iterator[MediaInfo]:
    for row in rows:
        (snap_name, id, media_type, media_url,
         media_name, media_hash, path) = row
        snap_name = snap_name.replace(',', ';')
        if not path:
            continue
        url = MEDIA_ROOT + quote(path)
        filename = os.path.basename(url)
        local = f'{media_dir}/{id}.{filename}'
        if not os.path.exists(local):
            while True:
                print(f'Downloading {snap_name} {local}')
                if download(url, local, media_hash):
                    break

        img = Image.open(local)
        framecount = getattr(img, 'n_frames', 0)
        fps = get_avg_fps(img)
        length = framecount * fps
        yield MediaInfo(
            snap_name=snap_name,
            media_type=media_type,
            filename=filename,
            format=img.format,
            width=img.width,
            height=img.height,
            aspect_ratio=calculate_aspect(img.width, img.height),
            size=os.path.getsize(local),
            framecount=framecount,
            fps=fps,
            length=length,
        )


def summary(rows: Iterator[MediaInfo]) -> None:
    counters = dict(
        media_types=collections.Counter(),
        aspect_ratios=collections.Counter(),
        formats=collections.Counter(),
        resolutions=collections.Counter(),
        screenshots=collections.Counter(),
        sizes=collections.Counter(),
        fps=collections.Counter(),
        length=collections.Counter(),
        totals=collections.Counter(),
    )

    for info in rows:
        if info.media_type == 'icon_256':
            media_type = 'icon'
        else:
            media_type = info.media_type

        counters['media_types'][media_type] += 1
        counters['formats'][info.format] += 1
        if media_type == 'screenshot':
            counters['aspect_ratios'][info.aspect_ratio] += 1
            counters['aspect_ratios']['Total'] += 1

        # Resolution
        resolutions = counters['resolutions']
        if media_type == 'icon':
            resolutions['ok'] += 1
        elif info.width < 480:
            resolutions['width too small'] += 1
        elif info.height < 480:
            resolutions['height too small'] += 1
        elif info.width > 3840:
            resolutions['width too big'] += 1
        elif info.height > 2160:
            resolutions['height too big'] += 1
        else:
            resolutions['ok'] += 1

        # File size
        sizes = counters['sizes']
        if media_type == 'icon_256' and info.size > 256 * 1024:
            sizes['icon too big'] += 1
        elif media_type == 'screenshot' and info.size > 2 * 1024 * 1024:
            sizes['screenshot too big'] += 1
        else:
            sizes[media_type] += 1

        screenshots = counters['screenshots']
        if media_type == 'screenshot':
            screenshots[info.snap_name] += 1
        else:
            if not info.snap_name in screenshots:
                screenshots[info.snap_name] = 0

        fps_counter = counters['fps']
        if info.fps == 0:
            pass
        elif info.fps < 1:
            fps_counter['< 1'] += 1
        elif info.fps > 30:
            fps_counter['> 30'] += 1
        else:
            fps_counter['1..30'] += 1

        length_counter = counters['length']
        if info.length == 0:
            pass
        elif info.length > 30:
            length_counter['> 30'] += 1
        else:
            length_counter['<= 30'] += 1

        counters['totals']['total'] += 1

    c = collections.Counter()
    for value in counters.pop('screenshots').values():
        if value >= 10:
            c['10+'] += 1
        else:
            c[str(value)] += 1
    counters['screenshots'] = c

    pprint.pprint(
        {name.capitalize(): counter.most_common(10)
         for name, counter in counters.items()}
    )



def main(filename: str) -> None:
    media_dir = 'media_files'
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)

    # \copy ($DB_QUERY) To '/tmp/filename.csv' WITH CSV;
    rows = csv.reader(open(filename, 'rt'))
    infos = parse_media(rows, media_dir)
    summary(infos)


if __name__ == '__main__':
    main('/home/jdahlin/scaprod-media.csv')
    #main(sys.argv[1])
