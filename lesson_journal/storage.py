from __future__ import annotations

import asyncio
import inspect
import json
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from .config import (
    BLOB_READ_WRITE_TOKEN,
    DATA_DIR,
    LESSON_DB_PATH,
    ROOT_DIR,
    STUDENT_INDEX_PATH,
    STUDENTS_DIR,
    UPLOAD_DIR,
)


_LOCK = Lock()
_LEGACY_LESSON_PREFIX = "lessons/"
_LEGACY_AUDIO_PREFIX = "audio/"
_STUDENT_PREFIX = "students/"
_STUDENT_INDEX_BLOB_PATH = f"{_STUDENT_PREFIX}index.json"


def normalize_student_slug(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return ""

    normalized = normalized.replace("\\", "-").replace("/", "-")
    normalized = re.sub(r"[^a-z0-9_-]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
    return normalized[:80]


def student_name_from_slug(student_slug: str) -> str:
    normalized = normalize_student_slug(student_slug)
    if not normalized:
        return ""

    label = re.sub(r"-[a-z0-9]{4,8}$", "", normalized)
    label = label.replace("-", " ").strip()
    return label or normalized


def uses_blob_storage() -> bool:
    return bool(BLOB_READ_WRITE_TOKEN)


def ensure_storage() -> None:
    if uses_blob_storage():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
    if not LESSON_DB_PATH.exists():
        LESSON_DB_PATH.write_text("[]", encoding="utf-8")
    if not STUDENT_INDEX_PATH.exists():
        STUDENT_INDEX_PATH.write_text("[]", encoding="utf-8")


def list_students() -> list[dict[str, Any]]:
    if uses_blob_storage():
        students = _read_students_blob()
    else:
        students = _read_students_local()
    return sorted(students, key=lambda item: (item.get("student_name", ""), item.get("student_slug", "")))


def get_student(student_slug: str) -> dict[str, Any] | None:
    normalized_slug = normalize_student_slug(student_slug)
    if not normalized_slug:
        return None

    students = _read_students_blob() if uses_blob_storage() else _read_students_local()
    for student in students:
        if normalize_student_slug(student.get("student_slug", "")) == normalized_slug:
            return student
    return None


def ensure_student(student_slug: str, student_name: str = "") -> dict[str, Any]:
    normalized_slug = normalize_student_slug(student_slug)
    if not normalized_slug:
        raise ValueError("student_slug is required")

    existing = get_student(normalized_slug)
    resolved_name = str(student_name or "").strip() or student_name_from_slug(normalized_slug)
    if existing is not None:
        if resolved_name and existing.get("student_name") != resolved_name:
            updated = {
                **existing,
                "student_name": resolved_name,
                "updated_at": _utc_now(),
            }
            _upsert_student(updated)
            return updated
        _ensure_local_student_scope(normalized_slug)
        return existing

    student = {
        "student_id": f"stu_{uuid.uuid4().hex[:10]}",
        "student_slug": normalized_slug,
        "student_name": resolved_name or normalized_slug,
        "status": "active",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    _upsert_student(student)
    _ensure_local_student_scope(normalized_slug)
    return student


def touch_student(student_slug: str) -> dict[str, Any] | None:
    existing = get_student(student_slug)
    if existing is None:
        return None

    updated = {
        **existing,
        "updated_at": _utc_now(),
    }
    _upsert_student(updated)
    return updated


def list_lessons(*, student_slug: str | None = None) -> list[dict[str, Any]]:
    if uses_blob_storage():
        return _sort_lessons(_read_all_blob(student_slug=student_slug))
    return _sort_lessons(_read_all_local(student_slug=student_slug))


def get_lesson(lesson_id: str, *, student_slug: str | None = None) -> dict[str, Any] | None:
    if uses_blob_storage():
        return _read_lesson_blob(lesson_id, student_slug=student_slug)

    for lesson in _read_all_local(student_slug=student_slug):
        if lesson.get("id") == lesson_id:
            return lesson
    return None


def create_lesson(record: dict[str, Any], *, student_slug: str | None = None) -> dict[str, Any]:
    normalized_slug = normalize_student_slug(student_slug or "")
    payload = {
        **record,
        "student_slug": normalized_slug,
    } if normalized_slug else dict(record)

    if uses_blob_storage():
        _write_lesson_blob(payload, student_slug=normalized_slug)
        return payload

    records = _read_all_local(student_slug=normalized_slug)
    records.append(payload)
    _write_all_local(records, student_slug=normalized_slug)
    return payload


def update_lesson(lesson_id: str, updates: dict[str, Any], *, student_slug: str | None = None) -> dict[str, Any] | None:
    normalized_slug = normalize_student_slug(student_slug or "")
    if uses_blob_storage():
        existing = _read_lesson_blob(lesson_id, student_slug=normalized_slug)
        if existing is None:
            return None
        merged = {**existing, **updates}
        if normalized_slug:
            merged["student_slug"] = normalized_slug
        _write_lesson_blob(merged, student_slug=normalized_slug)
        return merged

    records = _read_all_local(student_slug=normalized_slug)
    updated_record = None
    for index, lesson in enumerate(records):
        if lesson.get("id") != lesson_id:
            continue
        lesson.update(updates)
        if normalized_slug:
            lesson["student_slug"] = normalized_slug
        records[index] = lesson
        updated_record = lesson
        break
    if updated_record is None:
        return None
    _write_all_local(records, student_slug=normalized_slug)
    return updated_record


def delete_lesson(lesson_id: str, *, student_slug: str | None = None) -> bool:
    normalized_slug = normalize_student_slug(student_slug or "")
    if uses_blob_storage():
        existing = _read_lesson_blob(lesson_id, student_slug=normalized_slug)
        if existing is None:
            return False
        delete_blob_object(_lesson_blob_path(lesson_id, student_slug=normalized_slug))
        return True

    records = _read_all_local(student_slug=normalized_slug)
    filtered_records = [lesson for lesson in records if lesson.get("id") != lesson_id]
    if len(filtered_records) == len(records):
        return False
    _write_all_local(filtered_records, student_slug=normalized_slug)
    return True


def persist_audio_files(files: list[dict[str, Any]], *, student_slug: str | None = None) -> list[str]:
    if not files:
        return []
    if uses_blob_storage():
        return _persist_audio_files_blob(files, student_slug=student_slug)
    return _persist_audio_files_local(files, student_slug=student_slug)


def load_audio_input_content(file_info: dict[str, Any]) -> dict[str, Any]:
    if file_info.get("content") is not None:
        return file_info

    pathname = str(
        file_info.get("blob_pathname")
        or file_info.get("pathname")
        or file_info.get("blob_url_path")
        or ""
    ).strip()
    if not pathname:
        return file_info

    return {
        **file_info,
        "content": _download_blob_bytes(pathname),
    }


def cleanup_temporary_audio_inputs(files: list[dict[str, Any]]) -> None:
    for file_info in files:
        pathname = str(
            file_info.get("blob_pathname")
            or file_info.get("pathname")
            or file_info.get("blob_url_path")
            or ""
        ).strip()
        if pathname:
            delete_blob_object(pathname)


def _sort_lessons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda item: (item.get("lesson_date", ""), item.get("created_at", "")),
        reverse=True,
    )


def _read_all_local(*, student_slug: str | None = None) -> list[dict[str, Any]]:
    ensure_storage()
    lesson_path = _lesson_db_path(student_slug)
    if not lesson_path.exists():
        _initialize_local_json_file(lesson_path)
    with _LOCK:
        raw = lesson_path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    return json.loads(raw)


def _write_all_local(records: list[dict[str, Any]], *, student_slug: str | None = None) -> None:
    ensure_storage()
    lesson_path = _lesson_db_path(student_slug)
    lesson_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    with _LOCK:
        lesson_path.write_text(payload, encoding="utf-8")


def _persist_audio_files_local(files: list[dict[str, Any]], *, student_slug: str | None = None) -> list[str]:
    ensure_storage()
    upload_dir = _upload_dir(student_slug)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_paths: list[str] = []
    for file_info in files:
        suffix = Path(file_info.get("filename") or "").suffix or _guess_suffix(file_info.get("content_type") or "")
        destination = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        destination.write_bytes(file_info["content"])
        stored_paths.append(str(destination.relative_to(ROOT_DIR)))
    return stored_paths


def _persist_audio_files_blob(files: list[dict[str, Any]], *, student_slug: str | None = None) -> list[str]:
    client = _blob_client()
    stored_paths: list[str] = []
    audio_prefix = _audio_blob_prefix(student_slug)
    for file_info in files:
        suffix = Path(file_info.get("filename") or "").suffix or _guess_suffix(file_info.get("content_type") or "")
        pathname = f"{audio_prefix}{uuid.uuid4().hex}{suffix}"
        uploaded = client.put(
            pathname,
            file_info["content"],
            access="private",
            content_type=file_info.get("content_type") or "application/octet-stream",
        )
        stored_paths.append(getattr(uploaded, "pathname", pathname))
    return stored_paths


def _lesson_blob_path(lesson_id: str, student_slug: str | None = None) -> str:
    return f"{_lesson_blob_prefix(student_slug)}{lesson_id}.json"


def _lesson_blob_prefix(student_slug: str | None) -> str:
    normalized_slug = normalize_student_slug(student_slug or "")
    if not normalized_slug:
        return _LEGACY_LESSON_PREFIX
    return f"{_STUDENT_PREFIX}{normalized_slug}/lessons/"


def _audio_blob_prefix(student_slug: str | None) -> str:
    normalized_slug = normalize_student_slug(student_slug or "")
    if not normalized_slug:
        return _LEGACY_AUDIO_PREFIX
    return f"{_STUDENT_PREFIX}{normalized_slug}/audio/"


def _read_all_blob(*, student_slug: str | None = None) -> list[dict[str, Any]]:
    items = _list_blob_objects(prefix=_lesson_blob_prefix(student_slug))
    records: list[dict[str, Any]] = []
    for item in items:
        pathname = getattr(item, "pathname", None) or item.get("pathname")
        if not pathname:
            continue
        payload = _download_blob_json(pathname)
        if payload:
            records.append(payload)
    return records


def _read_lesson_blob(lesson_id: str, *, student_slug: str | None = None) -> dict[str, Any] | None:
    return _download_blob_json(_lesson_blob_path(lesson_id, student_slug=student_slug))


def _write_lesson_blob(record: dict[str, Any], *, student_slug: str | None = None) -> None:
    pathname = _lesson_blob_path(str(record["id"]), student_slug=student_slug)
    delete_blob_object(pathname)
    payload = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    _blob_client().put(pathname, payload, access="private", content_type="application/json")


def _read_students_local() -> list[dict[str, Any]]:
    ensure_storage()
    if not STUDENT_INDEX_PATH.exists():
        _initialize_local_json_file(STUDENT_INDEX_PATH)
    with _LOCK:
        raw = STUDENT_INDEX_PATH.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    return json.loads(raw)


def _write_students_local(records: list[dict[str, Any]]) -> None:
    ensure_storage()
    STUDENT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    with _LOCK:
        STUDENT_INDEX_PATH.write_text(payload, encoding="utf-8")


def _read_students_blob() -> list[dict[str, Any]]:
    payload = _download_blob_json(_STUDENT_INDEX_BLOB_PATH)
    if isinstance(payload, list):
        return payload
    return []


def _write_students_blob(records: list[dict[str, Any]]) -> None:
    delete_blob_object(_STUDENT_INDEX_BLOB_PATH)
    payload = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")
    _blob_client().put(_STUDENT_INDEX_BLOB_PATH, payload, access="private", content_type="application/json")


def _upsert_student(student: dict[str, Any]) -> None:
    normalized_slug = normalize_student_slug(student.get("student_slug", ""))
    if not normalized_slug:
        raise ValueError("student_slug is required")

    if uses_blob_storage():
        records = _read_students_blob()
    else:
        records = _read_students_local()

    updated = False
    for index, existing in enumerate(records):
        if normalize_student_slug(existing.get("student_slug", "")) != normalized_slug:
            continue
        records[index] = {
            **existing,
            **student,
            "student_slug": normalized_slug,
        }
        updated = True
        break

    if not updated:
        records.append({
            **student,
            "student_slug": normalized_slug,
        })

    if uses_blob_storage():
        _write_students_blob(records)
        return

    _write_students_local(records)


def _lesson_db_path(student_slug: str | None) -> Path:
    normalized_slug = normalize_student_slug(student_slug or "")
    if not normalized_slug:
        return LESSON_DB_PATH
    return STUDENTS_DIR / normalized_slug / "lessons.json"


def _upload_dir(student_slug: str | None) -> Path:
    normalized_slug = normalize_student_slug(student_slug or "")
    if not normalized_slug:
        return UPLOAD_DIR
    return STUDENTS_DIR / normalized_slug / "uploads"


def _ensure_local_student_scope(student_slug: str) -> None:
    if uses_blob_storage():
        return

    normalized_slug = normalize_student_slug(student_slug)
    if not normalized_slug:
        return

    student_dir = STUDENTS_DIR / normalized_slug
    student_dir.mkdir(parents=True, exist_ok=True)
    _initialize_local_json_file(student_dir / "lessons.json")
    (student_dir / "uploads").mkdir(parents=True, exist_ok=True)


def _initialize_local_json_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with _LOCK:
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def delete_blob_object(pathname: str) -> None:
    if not uses_blob_storage():
        return

    delete_fn = _blob_delete_function()
    try:
        delete_fn(pathname)
    except Exception:
        return


def _download_blob_json(pathname: str) -> Any:
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
        if result is None:
            return b""

        stream = getattr(result, "stream", None)
        if stream is not None:
            chunks = [chunk async for chunk in stream]
            return b"".join(chunks)

        body = getattr(result, "body", None)
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                return bytes(body)
            if hasattr(body, "__aiter__"):
                chunks = [chunk async for chunk in body]
                return b"".join(chunks)
            if hasattr(body, "read"):
                payload = body.read()
                if inspect.isawaitable(payload):
                    payload = await payload
                if isinstance(payload, (bytes, bytearray)):
                    return bytes(payload)
                if isinstance(payload, str):
                    return payload.encode("utf-8")

        content = getattr(result, "content", None)
        if content is not None:
            if isinstance(content, (bytes, bytearray)):
                return bytes(content)
            if isinstance(content, str):
                return content.encode("utf-8")

        read_method = getattr(result, "read", None)
        if callable(read_method):
            payload = read_method()
            if inspect.isawaitable(payload):
                payload = await payload
            if isinstance(payload, (bytes, bytearray)):
                return bytes(payload)
            if isinstance(payload, str):
                return payload.encode("utf-8")

        raise RuntimeError(
            f"Unsupported Vercel Blob get() result for {pathname}: {sorted(dir(result))}"
        )

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


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
