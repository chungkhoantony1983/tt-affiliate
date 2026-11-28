"""
Upload a finished video folder to Google Drive, one subfolder per product.

Layout:  <DRIVE_FOLDER_ID>/<product name>/<run folder name>/{video.mp4, post.txt, script.json, ...}

Uses the operator's own Google account (OAuth), not the sheet service account:
service accounts have no Drive storage, so they cannot own files in a personal Drive.

One-time setup:
  1. Google Cloud console → APIs & Services → enable "Google Drive API".
  2. Credentials → Create credentials → OAuth client ID → Desktop app → download JSON
     → save as google-oauth-client.json in the project root.
  3. OAuth consent screen → Publishing status "In production" (in "Testing" the login expires every 7 days).
  4. First upload opens a browser to log in; the token is saved to google-drive-token.json.
"""
import hashlib
import mimetypes
import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_FILE = "google-oauth-client.json"
TOKEN_FILE = "google-drive-token.json"
API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"
SKIP_PREFIXES = ("_",)  # render / layout temp files and backups (_scene_, _bo_, _mv_, _new_audio_, _rename_plan.json)
SKIP_NAMES = ("script.before-layout.json",)  # layout backup (DR-0014 C-0014-4)


def _session():
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials

    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # revoked or expired refresh token → log in again
    if not creds or not creds.valid:
        if not Path(CLIENT_FILE).exists():
            raise RuntimeError(f"{CLIENT_FILE} not found — see setup steps at the top of drive_upload.py")
        from google_auth_oauthlib.flow import InstalledAppFlow

        print("🔐 Opening the browser to log in to Google Drive (one time)...")
        creds = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES).run_local_server(port=0)
    Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
    return AuthorizedSession(creds)


def _check(resp):
    if resp.status_code >= 400:
        raise RuntimeError(f"Drive API {resp.status_code}: {resp.text[:300]}")
    return resp


def _find_or_create_folder(s, name: str, parent: str) -> str:
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{safe}' and '{parent}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false"
    found = _check(s.get(f"{API}/files", params={"q": q, "fields": "files(id)", "pageSize": 1,
                                                  "supportsAllDrives": "true",
                                                  "includeItemsFromAllDrives": "true"})).json()["files"]
    if found:
        return found[0]["id"]
    meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
    return _check(s.post(f"{API}/files", params={"fields": "id", "supportsAllDrives": "true"},
                         json=meta)).json()["id"]


def _find_file(s, name: str, parent: str):
    """Id of a non-folder file called `name` directly inside `parent`, or None."""
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{safe}' and '{parent}' in parents and mimeType != '{FOLDER_MIME}' and trashed = false"
    found = _check(s.get(f"{API}/files", params={"q": q, "fields": "files(id)", "pageSize": 1,
                                                  "supportsAllDrives": "true",
                                                  "includeItemsFromAllDrives": "true"})).json()["files"]
    return found[0]["id"] if found else None


def _upload_file(s, path: Path, parent: str, existing_id: str = None) -> dict:
    """Resumable upload (works for any size); returns {id, md5Checksum, size}.
    existing_id: replace the content of that Drive file instead of creating a second one."""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    params = {"uploadType": "resumable", "supportsAllDrives": "true", "fields": "id,md5Checksum,size"}
    if existing_id:
        start = _check(s.patch(f"{UPLOAD_API}/files/{existing_id}", params=params, json={"name": path.name},
                               headers={"X-Upload-Content-Type": mime}))
    else:
        start = _check(s.post(f"{UPLOAD_API}/files", params=params,
                              json={"name": path.name, "parents": [parent]},
                              headers={"X-Upload-Content-Type": mime}))
    with path.open("rb") as f:
        return _check(s.put(start.headers["Location"], data=f,
                            headers={"Content-Type": mime})).json()


def upload_video_folder(out_dir: Path, product_name: str, path=None, skip_prefixes=(),
                        replace_existing: bool = False) -> str:
    """Upload every file in out_dir to <root>/<product>/<out_dir name>/ and verify checksums.
    path: optional list of folder names (e.g. ["travel", "vn"]) used instead of [product_name].
    skip_prefixes: extra file-name prefixes that are not uploaded (e.g. stock clips).
    replace_existing: a file that is already in the Drive folder (same name) is updated in place, so approving
    again after a partial upload does not leave duplicates. Default False = old behaviour (always create).
    Returns the Drive link of the run folder. Raises if any file does not match."""
    root = os.environ.get("DRIVE_FOLDER_ID", "").strip()
    if not root:
        raise RuntimeError("DRIVE_FOLDER_ID not set in .env")
    s = _session()
    parent = root
    names = list(path) if path else [product_name.strip() or "Khác"]
    for name in names:
        parent = _find_or_create_folder(s, name, parent)
    run_folder = _find_or_create_folder(s, out_dir.name, parent)

    skip = SKIP_PREFIXES + tuple(skip_prefixes)
    files = sorted(p for p in out_dir.iterdir() if p.is_file() and not p.name.startswith(skip)
                   and p.name not in SKIP_NAMES)
    print(f"☁️  Uploading {len(files)} file(s) to Drive: {'/'.join(names)}/{out_dir.name}")
    for p in files:
        existing = _find_file(s, p.name, run_folder) if replace_existing else None
        info = _upload_file(s, p, run_folder, existing) if existing else _upload_file(s, p, run_folder)
        local_md5 = hashlib.md5(p.read_bytes()).hexdigest()
        if info.get("md5Checksum") != local_md5:
            raise RuntimeError(f"Checksum mismatch after uploading {p.name}")
    return f"https://drive.google.com/drive/folders/{run_folder}"
