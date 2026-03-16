from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("LESSON_JOURNAL_DATA_DIR", str(ROOT_DIR / "data"))).expanduser()
UPLOAD_DIR = DATA_DIR / "uploads"
LESSON_DB_PATH = DATA_DIR / "lessons.json"
STATIC_DIR = ROOT_DIR / "static"

HOST = os.getenv("LESSON_JOURNAL_HOST") or ("0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
PORT = int(os.getenv("LESSON_JOURNAL_PORT") or os.getenv("PORT") or "8000")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini").strip()
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe").strip()
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
LESSON_JOURNAL_BASIC_AUTH_USER = os.getenv("LESSON_JOURNAL_BASIC_AUTH_USER", "").strip()
LESSON_JOURNAL_BASIC_AUTH_PASSWORD = os.getenv("LESSON_JOURNAL_BASIC_AUTH_PASSWORD", "").strip()
