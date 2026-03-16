from __future__ import annotations

import base64
import json
import mimetypes
import os
import uuid
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .ai import AIProcessingError, create_lesson_outputs, enrich_lesson_record
from .config import (
    BLOB_READ_WRITE_TOKEN,
    HOST,
    LESSON_DB_PATH,
    LESSON_JOURNAL_BASIC_AUTH_PASSWORD,
    LESSON_JOURNAL_BASIC_AUTH_USER,
    OPENAI_API_KEY,
    PORT,
    STATIC_DIR,
)
from .storage import create_lesson, ensure_storage, get_lesson, list_lessons, persist_audio_files, update_lesson


class LessonJournalHandler(BaseHTTPRequestHandler):
    server_version = "LessonJournal/0.2"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/healthz":
            self.send_json({"ok": True})
            return
        if not self.ensure_authenticated():
            return
        if path == "/":
            self.serve_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            self.serve_file(STATIC_DIR / path.removeprefix("/static/"))
            return
        if path == "/api/config":
            self.send_json(
                {
                    "has_api_key": bool(OPENAI_API_KEY),
                    "storage_backend": "vercel_blob" if BLOB_READ_WRITE_TOKEN else "local_file",
                    "data_file": str(LESSON_DB_PATH),
                }
            )
            return
        if path == "/api/lessons":
            lessons = [self.serialize_lesson_for_list(enrich_lesson_record(item)) for item in list_lessons()]
            self.send_json({"lessons": lessons})
            return
        if path == "/api/lesson":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            lesson = get_lesson(lesson_id)
            if lesson is None:
                self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
                return
            self.send_json({"lesson": enrich_lesson_record(lesson)})
            return
        if path.startswith("/api/lessons/"):
            lesson_id = path.removeprefix("/api/lessons/")
            lesson = get_lesson(lesson_id)
            if lesson is None:
                self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
                return
            self.send_json({"lesson": enrich_lesson_record(lesson)})
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "요청한 경로를 찾지 못했습니다.")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not self.ensure_authenticated():
            return
        if path == "/api/lessons":
            self.handle_create_lesson()
            return
        if path == "/api/regenerate":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            self.handle_regenerate_lesson(lesson_id)
            return
        if path.startswith("/api/lessons/") and path.endswith("/regenerate"):
            lesson_id = path.split("/")[3]
            self.handle_regenerate_lesson(lesson_id)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "요청한 경로를 찾지 못했습니다.")

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not self.ensure_authenticated():
            return
        if path == "/api/lesson":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            self.handle_update_lesson(lesson_id)
            return
        if path.startswith("/api/lessons/"):
            lesson_id = path.removeprefix("/api/lessons/")
            self.handle_update_lesson(lesson_id)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "요청한 경로를 찾지 못했습니다.")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def ensure_authenticated(self) -> bool:
        if not LESSON_JOURNAL_BASIC_AUTH_USER or not LESSON_JOURNAL_BASIC_AUTH_PASSWORD:
            return True

        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            self.send_auth_required()
            return False

        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            self.send_auth_required()
            return False

        username, separator, password = decoded.partition(":")
        if (
            not separator
            or username != LESSON_JOURNAL_BASIC_AUTH_USER
            or password != LESSON_JOURNAL_BASIC_AUTH_PASSWORD
        ):
            self.send_auth_required()
            return False

        return True

    def send_auth_required(self) -> None:
        body = b"Authentication required."
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Lesson Journal"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_create_lesson(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "multipart/form-data 형식이 필요합니다.")
            return

        body = self.read_request_body()
        form, files = self.parse_multipart(body, content_type)

        lesson_date = (form.get("lesson_date") or datetime.now().date().isoformat()).strip()
        article_title = (form.get("article_title") or "").strip()
        note = (form.get("note") or "").strip()
        manual_transcript = (form.get("manual_transcript") or "").strip()
        tone_samples = normalize_text_lines(form.get("tone_samples") or "")
        keep_audio = parse_checkbox(form.get("keep_audio") or "false")
        audio_files = files.get("audio", [])

        if not manual_transcript and not audio_files:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "음성 파일을 올리거나 전사문을 입력해주세요.")
            return
        if audio_files and not manual_transcript and not OPENAI_API_KEY:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST,
                "현재 API 키가 없어 음성 자동 전사를 할 수 없습니다. 전사문을 직접 붙여넣거나 API 키를 설정해주세요.",
            )
            return

        original_filenames = [file_info.get("filename", "") for file_info in audio_files]

        try:
            generated = create_lesson_outputs(
                lesson_date=lesson_date,
                article_title=article_title,
                note=note,
                tone_samples=tone_samples,
                manual_transcript=manual_transcript,
                audio_inputs=audio_files,
            )
        except AIProcessingError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return

        lesson_id = uuid.uuid4().hex[:12]
        now = utc_now()
        stored_audio_paths = persist_audio_files(audio_files) if keep_audio else []

        lesson = enrich_lesson_record(
            {
                "id": lesson_id,
                "lesson_date": lesson_date,
                "article_title": generated["resolved_article_title"],
                "note": note,
                "tone_samples": tone_samples,
                "audio_file_paths": stored_audio_paths,
                "original_audio_names": original_filenames,
                "transcript_text": generated["transcript_text"],
                "transcript_origin": generated["transcript_origin"],
                "generation_source": generated["generation_source"],
                "speaker_turns": generated["speaker_turns"],
                "dialogue_summary": generated["dialogue_summary"],
                "lesson_headline": generated["lesson_headline"],
                "student_summary": generated["student_summary"],
                "parent_summary": generated["parent_summary"],
                "notion_exports": generated["notion_exports"],
                "status": "complete",
                "created_at": now,
                "updated_at": now,
            }
        )

        create_lesson(lesson)
        self.send_json({"lesson": lesson}, status=HTTPStatus.CREATED)

    def handle_regenerate_lesson(self, lesson_id: str) -> None:
        lesson = get_lesson(lesson_id)
        if lesson is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
            return

        lesson = enrich_lesson_record(lesson)

        try:
            generated = create_lesson_outputs(
                lesson_date=lesson.get("lesson_date", ""),
                article_title=lesson.get("article_title", ""),
                note=lesson.get("note", ""),
                tone_samples=lesson.get("tone_samples", []),
                manual_transcript=lesson.get("transcript_text", ""),
                audio_inputs=[],
            )
        except AIProcessingError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return

        updated_record = enrich_lesson_record(
            {
                **lesson,
                "article_title": generated["resolved_article_title"],
                "transcript_text": generated["transcript_text"],
                "transcript_origin": generated["transcript_origin"],
                "generation_source": generated["generation_source"],
                "speaker_turns": generated["speaker_turns"],
                "dialogue_summary": generated["dialogue_summary"],
                "lesson_headline": generated["lesson_headline"],
                "student_summary": generated["student_summary"],
                "parent_summary": generated["parent_summary"],
                "notion_exports": generated["notion_exports"],
                "updated_at": utc_now(),
            }
        )
        updated = update_lesson(lesson_id, updated_record)
        self.send_json({"lesson": updated})

    def handle_update_lesson(self, lesson_id: str) -> None:
        lesson = get_lesson(lesson_id)
        if lesson is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
            return

        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        lesson = enrich_lesson_record(lesson)
        merged = enrich_lesson_record(
            {
                **lesson,
                "article_title": payload.get("article_title", lesson.get("article_title", "")),
                "lesson_headline": payload.get("lesson_headline", lesson.get("lesson_headline", "")),
                "student_summary": payload.get("student_summary", lesson.get("student_summary", {})),
                "parent_summary": payload.get("parent_summary", lesson.get("parent_summary", {})),
                "dialogue_summary": payload.get("dialogue_summary", lesson.get("dialogue_summary", "")),
                "updated_at": utc_now(),
            }
        )
        updated = update_lesson(lesson_id, merged)
        self.send_json({"lesson": updated})

    def read_request_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

    def parse_multipart(
        self,
        body: bytes,
        content_type: str,
    ) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
        header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        message = BytesParser(policy=default).parsebytes(header + body)

        form: dict[str, str] = {}
        files: dict[str, list[dict[str, Any]]] = {}

        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue

            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                files.setdefault(name, []).append(
                    {
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "content": payload,
                    }
                )
                continue

            charset = part.get_content_charset() or "utf-8"
            form[name] = payload.decode(charset, errors="replace")

        return form, files

    def serialize_lesson_for_list(self, lesson: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": lesson.get("id"),
            "lesson_date": lesson.get("lesson_date"),
            "article_title": lesson.get("article_title"),
            "lesson_headline": lesson.get("lesson_headline"),
            "dialogue_summary": lesson.get("dialogue_summary"),
            "one_line_feeling": lesson.get("student_summary", {}).get("one_line_feeling", ""),
            "audio_file_count": lesson.get("audio_file_count", 0),
            "status": lesson.get("status"),
            "updated_at": lesson.get("updated_at"),
        }

    def serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "파일을 찾지 못했습니다.")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        payload = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status=status)


def normalize_text_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def parse_checkbox(value: str) -> bool:
    return value.lower() in {"1", "true", "on", "yes"}


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0].strip() if values else ""


def run() -> None:
    ensure_storage()
    os.chdir(ROOT_DIR)
    server = ThreadingHTTPServer((HOST, PORT), LessonJournalHandler)
    print(f"Lesson Journal App running at http://{HOST}:{PORT}")
    server.serve_forever()
