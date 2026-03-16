from __future__ import annotations

import asyncio
import json
import mimetypes
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from .config import BLOB_READ_WRITE_TOKEN, DATA_DIR, LESSON_DB_PATH, ROOT_DIR, UPLOAD_DIR


_LOCK = Lock()
_LESSON_PREFIX = "lessons/"
_AUDIO_PREFIX = "audio/"


def uses_blob_storage() -> bool:
    return bool(BLOB_READ_WRITE_TOKEN)


def ensure_storage() -> None:
    if uses_blob_storage():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not LESSON_DB_PATH.exists():
        LESSON_DB_PATH.write_text("[]", encoding="utf-8")


def list_lessons() -> list[dict[str, Any]]:
    if uses_blob_storage():
        return _sort_lessons(_read_all_blob())
    return _sort_lessons(_read_all_local())


def get_lesson(lesson_id: str) -> dict[str, Any] | None:
    if uses_blob_storage():
        return _read_lesson_blob(lesson_id)

    for lesson in _read_all_local():
        if lesson.get("id") == lesson_id:
            return lesson
    return None


def create_lesson(record: dict[str, Any]) -> dict[str, Any]:
    if uses_blob_storage():
        _write_lesson_blob(record)
        return record

    records = _read_all_local()
    records.append(record)
    _write_all_local(records)
    return record


def update_lesson(lesson_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if uses_blob_storage():
        existing = _read_lesson_blob(lesson_id)
        if existing is None:
            return None
        merged = {**existing, **updates}
        _write_lesson_blob(merged)
        return merged

    records = _read_all_local()
    updated_record = None
    for index, lesson in enumerate(records):
        if lesson.get("id") != lesson_id:
            continue
        lesson.update(updates)
        records[index] = lesson
        updated_record = lesson
        break
    if updated_record is None:
        return None
    _write_all_local(records)
    return updated_record


def persist_audio_files(files: list[dict[str, Any]]) -> list[str]:
    if not files:
        return []
    if uses_blob_storage():
        return _persist_audio_files_blob(files)
    return _persist_audio_files_local(files)


def _sort_lessons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda item: (item.get("lesson_date", ""), item.get("created_at", "")),
        reverse=True,
    )


def _read_all_local() -> list[dict[str, Any]]:
    ensure_storage()
    with _LOCK:
        raw = LESSON_DB_PATH.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    return json.loads(raw)


def _write_all_local(records: list[dict[str, Any]]) -> None:
    ensure_storage()
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    with _LOCK:
        LESSON_DB_PATH.write_text(payload, encoding="utf-8")


def _persist_audio_files_local(files: list[dict[str, Any]]) -> list[str]:
    ensure_storage()
    stored_paths: list[str] = []
    for file_info in files:
        suffix = Path(file_info.get("filename") or "").suffix or _guess_suffix(file_info.get("content_type") or "")
        destination = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
        destination.write_bytes(file_info["content"])
        stored_paths.append(str(destination.relative_to(ROOT_DIR)))
    return stored_paths


def _persist_audio_files_blob(files: list[dict[str, Any]]) -> list[str]:
    client = _blob_client()
    stored_paths: list[str] = []
    for file_info in files:
        suffix = Path(file_info.get("filename") or "").suffix or _guess_suffix(file_info.get("content_type") or "")
        pathname = f"{_AUDIO_PREFIX}{uuid.uuid4().hex}{suffix}"
        uploaded = client.put(
            pathname,
            file_info["content"],
            access="private",
            content_type=file_info.get("content_type") or "application/octet-stream",
        )
        stored_paths.append(getattr(uploaded, "pathname", pathname))
    return stored_paths


def _lesson_blob_path(lesson_id: str) -> str:
    return f"{_LESSON_PREFIX}{lesson_id}.json"


def _read_all_blob() -> list[dict[str, Any]]:
    items = _list_blob_objects(prefix=_LESSON_PREFIX)
    records: list[dict[str, Any]] = []
    for item in items:
        pathname = getattr(item, "pathname", None) or item.get("pathname")
        if not pathname:
            continue
        payload = _download_blob_json(pathname)
        if payload:
            records.append(payload)
    return records


def _read_lesson_blob(lesson_id: str) -> dict[str, Any] | None:
    return _download_blob_json(_lesson_blob_path(lesson_id))


def _write_lesson_blob(record: dict[str, Any]) -> None:
    pathname = _lesson_blob_path(str(record["id"]))
    delete_blob_object(pathname)
    payload = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    _blob_client().put(pathname, payload, access="private", content_type="application/json")


def delete_blob_object(pathname: str) -> None:
    if not uses_blob_storage():
        return

    delete_fn = _blob_delete_function()
    try:
        delete_fn(pathname)
    except Exception:
        # Ignore missing objects so updates can overwrite cleanly.
        return


def _download_blob_json(pathname: str) -> dict[str, Any] | None:
    try:
        payload = _download_blob_bytes(pathname)
    except Exception:
        return None
    if not payload:
        return None
    return json.loads(payload.decode("utf-8-sig"))


def _download_blob_bytes(pathname: str) -> bytes:
    async def _runner() -> bytes:
        client = _async_blob_client()
        result = await client.get(pathname, access="private")
        chunks = [chunk async for chunk in result.stream]
        return b"".join(chunks)

    return asyncio.run(_runner())


def _list_blob_objects(*, prefix: str) -> list[Any]:
    list_objects = _blob_list_function()
    cursor = None
    blobs: list[Any] = []

    while True:
        result = list_objects(prefix=prefix, cursor=cursor, limit=100)
        page_blobs = getattr(result, "blobs", None)
        if page_blobs is None and isinstance(result, dict):
            page_blobs = result.get("blobs", [])
        blobs.extend(page_blobs or [])

        has_more = getattr(result, "has_more", None)
        if has_more is None and isinstance(result, dict):
            has_more = result.get("has_more")
        cursor = getattr(result, "cursor", None)
        if cursor is None and isinstance(result, dict):
            cursor = result.get("cursor")
        if not has_more or not cursor:
            break

    return blobs


def _blob_client():
    try:
        from vercel.blob import BlobClient
    except ImportError as exc:
        raise RuntimeError("Vercel Blob storage를 사용하려면 `vercel` 패키지가 필요합니다.") from exc

    return BlobClient(token=BLOB_READ_WRITE_TOKEN)


def _async_blob_client():
    try:
        from vercel.blob import AsyncBlobClient
    except ImportError as exc:
        raise RuntimeError("Vercel Blob storage를 사용하려면 `vercel` 패키지가 필요합니다.") from exc

    return AsyncBlobClient(token=BLOB_READ_WRITE_TOKEN)


def _blob_list_function():
    try:
        from vercel.blob import list_objects
    except ImportError as exc:
        raise RuntimeError("Vercel Blob storage를 사용하려면 `vercel` 패키지가 필요합니다.") from exc

    return lambda **kwargs: list_objects(token=BLOB_READ_WRITE_TOKEN, **kwargs)


def _blob_delete_function():
    try:
        from vercel.blob import delete
    except ImportError as exc:
        raise RuntimeError("Vercel Blob storage를 사용하려면 `vercel` 패키지가 필요합니다.") from exc

    return lambda pathname: delete(pathname, token=BLOB_READ_WRITE_TOKEN)


def _guess_suffix(content_type: str) -> str:
    return mimetypes.guess_extension(content_type) or ".bin"
