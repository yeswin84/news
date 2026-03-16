from __future__ import annotations

import json
from threading import Lock
from typing import Any

from .config import DATA_DIR, LESSON_DB_PATH, UPLOAD_DIR


_LOCK = Lock()


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not LESSON_DB_PATH.exists():
        LESSON_DB_PATH.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict[str, Any]]:
    ensure_storage()
    with _LOCK:
        raw = LESSON_DB_PATH.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    return json.loads(raw)


def _write_all(records: list[dict[str, Any]]) -> None:
    ensure_storage()
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    with _LOCK:
        LESSON_DB_PATH.write_text(payload, encoding="utf-8")


def _sort_lessons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda item: (item.get("lesson_date", ""), item.get("created_at", "")),
        reverse=True,
    )


def list_lessons() -> list[dict[str, Any]]:
    return _sort_lessons(_read_all())


def get_lesson(lesson_id: str) -> dict[str, Any] | None:
    for lesson in _read_all():
        if lesson.get("id") == lesson_id:
            return lesson
    return None


def create_lesson(record: dict[str, Any]) -> dict[str, Any]:
    records = _read_all()
    records.append(record)
    _write_all(records)
    return record


def update_lesson(lesson_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    records = _read_all()
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
    _write_all(records)
    return updated_record
