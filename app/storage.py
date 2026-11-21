import json
import os
import uuid
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
PUBLIC_BUCKET = os.environ.get("SUPABASE_PUBLIC_BUCKET", "media").strip() or "media"
PRIVATE_BUCKET = os.environ.get("SUPABASE_PRIVATE_BUCKET", "orders-private").strip() or "orders-private"

SB_PREFIX = "sb://"


def enabled():
    return bool(SUPABASE_URL and SERVICE_KEY)


def _headers(extra=None):
    h = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}
    if extra:
        h.update(extra)
    return h


def _call(method, url, data=None, headers=None, timeout=30, raw=False):
    req = Request(url, data=data, method=method, headers=_headers(headers))
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body) if body and not raw else body


def _object_path(ref):
    if ref.startswith(SB_PREFIX):
        bucket, _, name = ref[len(SB_PREFIX):].partition("/")
        return bucket, name
    public_prefix = f"{SUPABASE_URL}/storage/v1/object/public/"
    if ref.startswith(public_prefix):
        bucket, _, name = ref[len(public_prefix):].partition("/")
        return bucket, name
    return None, None


def upload(data, folder, ext, content_type, public):
    name = f"{folder}/{uuid.uuid4().hex}.{ext}"
    bucket = PUBLIC_BUCKET if public else PRIVATE_BUCKET
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{quote(name)}"
    _call("PUT", url, data=data, headers={
        "Content-Type": content_type or "application/octet-stream",
        "x-upsert": "true",
    }, timeout=60)
    if public:
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{quote(name)}"
    return f"{SB_PREFIX}{bucket}/{name}"


def signed_url(ref, expires=3600):
    bucket, name = _object_path(ref)
    if not bucket:
        return None
    body = json.dumps({"expiresIn": int(expires)}).encode()
    data = _call(
        "POST",
        f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{quote(name)}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    signed = data.get("signedURL") or ""
    if not signed:
        return None
    return SUPABASE_URL + signed


def delete(ref):
    bucket, name = _object_path(ref)
    if not bucket:
        return
    try:
        _call("DELETE", f"{SUPABASE_URL}/storage/v1/object/{bucket}/{quote(name)}")
    except (HTTPError, OSError):
        pass


def ensure_buckets():
    if not enabled():
        return
    for bucket, public in ((PUBLIC_BUCKET, True), (PRIVATE_BUCKET, False)):
        body = json.dumps({"id": bucket, "name": bucket, "public": public}).encode()
        try:
            _call("POST", f"{SUPABASE_URL}/storage/v1/bucket", data=body,
                  headers={"Content-Type": "application/json"})
        except HTTPError:
            pass
        except OSError:
            pass
