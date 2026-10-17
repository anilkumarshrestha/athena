"""Media store: local directory in dev, GCS bucket when MEDIA_BUCKET is set.

Always served through /api/media/{id}, so the bucket stays private.
"""

import re
import uuid
from functools import lru_cache
from pathlib import Path

from athena.config import settings

LOCAL_DIR = Path(__file__).resolve().parent.parent / "media"
_ID = re.compile(r"^[0-9a-f]{32}\.(png|jpeg|jpg|webp)$")
_EXT = {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}
_MIME = {v: k for k, v in _EXT.items()} | {"jpg": "image/jpeg"}


@lru_cache
def _bucket():
    from google.cloud import storage

    return storage.Client(project=settings().google_cloud_project).bucket(settings().media_bucket)


def save(data: bytes, mime: str) -> str:
    media_id = f"{uuid.uuid4().hex}.{_EXT.get(mime, 'png')}"
    if settings().media_bucket:
        _bucket().blob(f"images/{media_id}").upload_from_string(data, content_type=mime)
    else:
        LOCAL_DIR.mkdir(exist_ok=True)
        (LOCAL_DIR / media_id).write_bytes(data)
    return media_id


def load(media_id: str) -> tuple[bytes, str] | None:
    if not _ID.match(media_id):  # also blocks path traversal
        return None
    mime = _MIME[media_id.rsplit(".", 1)[1]]
    if settings().media_bucket:
        blob = _bucket().blob(f"images/{media_id}")
        return (blob.download_as_bytes(), mime) if blob.exists() else None
    path = LOCAL_DIR / media_id
    return (path.read_bytes(), mime) if path.exists() else None
