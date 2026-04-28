from __future__ import annotations

import base64
import json
import mimetypes
import os
import socket
import traceback
import uuid
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .academy import (
    generate_student_report_draft,
    get_academy_bootstrap,
    update_selected_student,
    update_student_lesson,
    update_student_report,
    update_student_test,
)
from .academy_pdf import generate_academy_report_pdf
from .ai import AIProcessingError, create_lesson_outputs, enrich_lesson_record
from .config import (
    BLOB_READ_WRITE_TOKEN,
    HOST,
    LESSON_DB_PATH,
    LESSON_JOURNAL_BASIC_AUTH_PASSWORD,
    LESSON_JOURNAL_BASIC_AUTH_USER,
    OPENAI_API_KEY,
    PORT,
    ROOT_DIR,
    STATIC_DIR,
)
from .storage import (
    cleanup_temporary_audio_inputs,
    create_lesson,
    delete_lesson,
    ensure_storage,
    ensure_student,
    get_student,
    get_lesson,
    list_lessons,
    list_students,
    normalize_student_slug,
    touch_student,
    update_lesson,
)


class StudentContextError(RuntimeError):
    """Raised when the request student context is invalid."""


class LessonJournalHandler(BaseHTTPRequestHandler):
    server_version = "LessonJournal/0.4"

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
        if path in {"/academy-ui", "/academy-ui/"}:
            self.serve_file(STATIC_DIR / "academy-ui.html")
            return
        if path in {"/admin", "/admin/"}:
            self.serve_file(STATIC_DIR / "admin.html")
            return

        student_page_slug = extract_student_slug_from_app_path(path)
        if student_page_slug:
            ensure_student(student_page_slug)
            self.serve_file(STATIC_DIR / "index.html")
            return

        if path.startswith("/static/"):
            self.serve_file(STATIC_DIR / path.removeprefix("/static/"))
            return
        if path == "/api/admin/students":
            self.send_json(self.build_admin_students_payload())
            return
        if path == "/api/admin/student-lessons":
            student_slug = normalize_student_slug(first_query_value(query, "slug"))
            if not student_slug:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "학생 slug가 필요합니다.")
                return
            student = get_student(student_slug)
            if student is None:
                self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
                return
            lessons = [
                self.serialize_lesson_for_list(enrich_lesson_record(item))
                for item in list_lessons(student_slug=student_slug)
            ]
            self.send_json(
                {
                    "student": self.build_admin_student_summary(student),
                    "lessons": lessons,
                }
            )
            return

        try:
            student = self.resolve_student_context(path, query)
        except StudentContextError as exc:
            self.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
            return

        if path == "/api/config":
            self.send_json(
                {
                    "has_api_key": bool(OPENAI_API_KEY),
                    "storage_backend": "vercel_blob" if BLOB_READ_WRITE_TOKEN else "local_file",
                    "supports_client_uploads": bool(BLOB_READ_WRITE_TOKEN and os.getenv("VERCEL")),
                    "data_file": str(LESSON_DB_PATH),
                    "local_url": build_local_url(PORT),
                    "network_url": build_network_url(PORT),
                    "mode": "student" if student else "global",
                    "student": self.serialize_student(student),
                }
            )
            return
        if path == "/api/academy/bootstrap":
            self.send_json(get_academy_bootstrap())
            return
        if path == "/api/academy/student-report/pdf":
            student_id = first_query_value(query, "student_id") or get_academy_bootstrap().get("workspace", {}).get("selected_student_id", "")
            if not student_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
                return
            self.handle_download_academy_student_report_pdf(student_id)
            return
        if path == "/api/context":
            self.send_json(self.build_context_payload(student))
            return
        if path == "/api/lessons":
            lessons = [
                self.serialize_lesson_for_list(enrich_lesson_record(item))
                for item in list_lessons(student_slug=self.student_slug(student))
            ]
            self.send_json({"lessons": lessons})
            return
        if path == "/api/lesson":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            lesson = get_lesson(lesson_id, student_slug=self.student_slug(student))
            if lesson is None:
                self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
                return
            self.send_json({"lesson": enrich_lesson_record(lesson)})
            return
        if path.startswith("/api/lessons/"):
            lesson_id = path.removeprefix("/api/lessons/")
            lesson = get_lesson(lesson_id, student_slug=self.student_slug(student))
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

        try:
            student = self.resolve_student_context(path, query)
        except StudentContextError as exc:
            self.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
            return

        if path == "/api/admin/students":
            self.handle_create_student()
            return
        if path == "/api/academy/select-student":
            self.handle_select_academy_student()
            return
        if path == "/api/academy/student-lesson":
            self.handle_update_academy_student_lesson()
            return
        if path == "/api/academy/student-test":
            self.handle_update_academy_student_test()
            return
        if path == "/api/academy/student-report/generate":
            self.handle_generate_academy_student_report()
            return
        if path == "/api/academy/student-report":
            self.handle_update_academy_student_report()
            return
        if path == "/api/lessons":
            self.handle_create_lesson(student)
            return
        if path == "/api/regenerate":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            self.handle_regenerate_lesson(lesson_id, student)
            return
        if path.startswith("/api/lessons/") and path.endswith("/regenerate"):
            lesson_id = path.split("/")[3]
            self.handle_regenerate_lesson(lesson_id, student)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "요청한 경로를 찾지 못했습니다.")

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not self.ensure_authenticated():
            return

        try:
            student = self.resolve_student_context(path, query)
        except StudentContextError as exc:
            self.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
            return

        if path == "/api/lesson":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            self.handle_update_lesson(lesson_id, student)
            return
        if path.startswith("/api/lessons/"):
            lesson_id = path.removeprefix("/api/lessons/")
            self.handle_update_lesson(lesson_id, student)
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "요청한 경로를 찾지 못했습니다.")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not self.ensure_authenticated():
            return

        try:
            student = self.resolve_student_context(path, query)
        except StudentContextError as exc:
            self.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
            return

        if path == "/api/lesson":
            lesson_id = first_query_value(query, "id")
            if not lesson_id:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "기록 id가 필요합니다.")
                return
            self.handle_delete_lesson(lesson_id, student)
            return
        if path.startswith("/api/lessons/"):
            lesson_id = path.removeprefix("/api/lessons/")
            self.handle_delete_lesson(lesson_id, student)
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
        self.send_header("WWW-Authenticate", 'Basic realm="Reading Note"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def resolve_student_context(self, path: str, query: dict[str, list[str]]) -> dict[str, Any] | None:
        raw_query_slug = first_query_value(query, "student") or self.headers.get("X-Lesson-Student", "").strip()
        query_slug = normalize_student_slug(raw_query_slug)
        referer_slug = extract_student_slug_from_url(self.headers.get("Referer", ""))
        path_slug = extract_student_slug_from_app_path(path)

        if raw_query_slug and not query_slug:
            raise StudentContextError("학생 링크 정보가 올바르지 않습니다.")
        if query_slug and referer_slug and query_slug != referer_slug:
            raise StudentContextError("학생 링크 정보가 현재 페이지와 일치하지 않습니다.")

        resolved_slug = query_slug or referer_slug or path_slug
        if not resolved_slug:
            return None

        return ensure_student(resolved_slug)

    def student_slug(self, student: dict[str, Any] | None) -> str | None:
        if not student:
            return None
        return normalize_student_slug(student.get("student_slug", ""))

    def build_context_payload(self, student: dict[str, Any] | None) -> dict[str, Any]:
        student_slug = self.student_slug(student)
        if not student_slug:
            lessons = list_lessons()
            return {
                "mode": "global",
                "student": None,
                "summary": {
                    "lesson_count": len(lessons),
                    "latest_lesson_date": lessons[0].get("lesson_date", "") if lessons else "",
                },
            }

        lessons = list_lessons(student_slug=student_slug)
        return {
            "mode": "student",
            "student": self.serialize_student(student),
            "summary": {
                "lesson_count": len(lessons),
                "latest_lesson_date": lessons[0].get("lesson_date", "") if lessons else "",
            },
        }

    def build_admin_students_payload(self) -> dict[str, Any]:
        students = [self.build_admin_student_summary(student) for student in list_students()]
        return {
            "summary": {
                "student_count": len(students),
                "submitted_today_count": sum(1 for item in students if item.get("progress_status") == "submitted_today"),
                "needs_attention_count": sum(1 for item in students if item.get("progress_status") == "needs_attention"),
                "not_started_count": sum(1 for item in students if item.get("progress_status") == "not_started"),
            },
            "students": students,
        }

    def build_admin_student_summary(self, student: dict[str, Any]) -> dict[str, Any]:
        student_slug = normalize_student_slug(student.get("student_slug", ""))
        lessons = [enrich_lesson_record(item) for item in list_lessons(student_slug=student_slug)]
        latest = lessons[0] if lessons else None
        progress_status, progress_label = derive_progress_status(
            latest_lesson_date=latest.get("lesson_date", "") if latest else "",
            lesson_count=len(lessons),
        )
        return {
            **self.serialize_student(student),
            "student_path": build_student_path(student_slug),
            "lesson_count": len(lessons),
            "latest_lesson_date": latest.get("lesson_date", "") if latest else "",
            "latest_lesson_title": latest.get("article_title", "") if latest else "",
            "latest_lesson_headline": latest.get("lesson_headline", "") if latest else "",
            "latest_one_line_feeling": latest.get("student_summary", {}).get("one_line_feeling", "") if latest else "",
            "progress_status": progress_status,
            "progress_label": progress_label,
        }

    def serialize_student(self, student: dict[str, Any] | None) -> dict[str, Any] | None:
        if not student:
            return None

        return {
            "student_id": student.get("student_id"),
            "student_slug": student.get("student_slug"),
            "student_name": student.get("student_name"),
            "status": student.get("status", "active"),
            "created_at": student.get("created_at"),
            "updated_at": student.get("updated_at"),
        }

    def handle_create_student(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_name = str(payload.get("student_name") or "").strip()
        requested_slug = normalize_student_slug(payload.get("student_slug") or "")
        if not student_name and not requested_slug:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "학생 이름이 필요합니다.")
            return

        student_slug = requested_slug or generate_student_slug(student_name)
        while get_student(student_slug) is not None:
            student_slug = generate_student_slug(student_name)

        student = ensure_student(student_slug, student_name=student_name)
        self.send_json({"student": self.build_admin_student_summary(student)}, status=HTTPStatus.CREATED)

    def handle_select_academy_student(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_id = str(payload.get("student_id") or "").strip()
        if not student_id:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
            return

        update_selected_student(student_id)
        self.send_json({"ok": True, "student_id": student_id})

    def handle_update_academy_student_lesson(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_id = str(payload.get("student_id") or "").strip()
        if not student_id:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
            return

        try:
            student = update_student_lesson(
                student_id=student_id,
                natural_note=str(payload.get("natural_note") or "").strip(),
                achievement=str(payload.get("achievement") or "").strip(),
                homework=str(payload.get("homework") or "").strip(),
                difficulty=str(payload.get("difficulty") or "").strip(),
                next_step=str(payload.get("next_step") or "").strip(),
                tags=[str(item).strip() for item in payload.get("tags", []) if str(item).strip()],
            )
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
            return

        self.send_json({"ok": True, "student": student})

    def handle_update_academy_student_test(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_id = str(payload.get("student_id") or "").strip()
        if not student_id:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
            return

        try:
            score_value = int(payload.get("score_value", 0))
        except (TypeError, ValueError):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "score_value는 숫자여야 합니다.")
            return

        try:
            student = update_student_test(
                student_id=student_id,
                score_value=score_value,
                trend_label=str(payload.get("trend_label") or "").strip(),
                strength=str(payload.get("strength") or "").strip(),
                weakness=str(payload.get("weakness") or "").strip(),
                plan=str(payload.get("plan") or "").strip(),
                weak_concepts=[str(item).strip() for item in payload.get("weak_concepts", []) if str(item).strip()],
            )
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
            return

        self.send_json({"ok": True, "student": student})

    def handle_generate_academy_student_report(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_id = str(payload.get("student_id") or "").strip()
        if not student_id:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
            return

        try:
            student = generate_student_report_draft(student_id=student_id)
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
            return

        self.send_json({"ok": True, "student": student})

    def handle_update_academy_student_report(self) -> None:
        try:
            payload = json.loads(self.read_request_body().decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
            return

        student_id = str(payload.get("student_id") or "").strip()
        if not student_id:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "student_id가 필요합니다.")
            return

        try:
            student = update_student_report(
                student_id=student_id,
                summary=str(payload.get("summary") or "").strip(),
                attitude=str(payload.get("attitude") or "").strip(),
                achievement=str(payload.get("achievement") or "").strip(),
                homework=str(payload.get("homework") or "").strip(),
                difficulty=str(payload.get("difficulty") or "").strip(),
                test=str(payload.get("test") or "").strip(),
                next_step=str(payload.get("next_step") or "").strip(),
                message_draft=str(payload.get("message_draft") or "").strip(),
            )
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
            return

        self.send_json({"ok": True, "student": student})

    def handle_download_academy_student_report_pdf(self, student_id: str) -> None:
        try:
            pdf_payload = generate_academy_report_pdf(student_id)
        except KeyError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "학생을 찾지 못했습니다.")
            return
        except FileNotFoundError as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        self.send_binary(
            pdf_payload["content"],
            content_type="application/pdf",
            filename=pdf_payload["filename"],
        )

    def handle_create_lesson(self, student: dict[str, Any] | None) -> None:
        content_type = self.headers.get("Content-Type", "")
        audio_files: list[dict[str, Any]] = []

        if content_type.startswith("multipart/form-data"):
            body = self.read_request_body()
            form, files = self.parse_multipart(body, content_type)

            lesson_date = (form.get("lesson_date") or datetime.now().date().isoformat()).strip()
            article_title = (form.get("article_title") or "").strip()
            article_url = (form.get("article_url") or "").strip()
            article_text = (form.get("article_text") or "").strip()
            note = (form.get("note") or "").strip()
            manual_transcript = (form.get("manual_transcript") or "").strip()
            tone_samples = normalize_text_lines(form.get("tone_samples") or "")
            audio_files = files.get("audio", [])
        elif content_type.startswith("application/json"):
            try:
                payload = json.loads(self.read_request_body().decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 형식이 올바르지 않습니다.")
                return

            lesson_date = str(payload.get("lesson_date") or datetime.now().date().isoformat()).strip()
            article_title = str(payload.get("article_title") or "").strip()
            article_url = str(payload.get("article_url") or "").strip()
            article_text = str(payload.get("article_text") or "").strip()
            note = str(payload.get("note") or "").strip()
            manual_transcript = str(payload.get("manual_transcript") or "").strip()
            tone_samples = normalize_text_value(payload.get("tone_samples"))
            audio_files = normalize_audio_refs(payload.get("audio_refs") or [])
        else:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "multipart/form-data 또는 application/json 형식이 필요합니다.")
            return

        if not manual_transcript and not audio_files and not article_text:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "음성 파일을 올리거나 텍스트를 입력해주세요.")
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
                article_url=article_url,
                article_text=article_text,
                note=note,
                tone_samples=tone_samples,
                manual_transcript=manual_transcript,
                audio_inputs=audio_files,
            )
        except AIProcessingError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except Exception as exc:
            print("Unexpected error in handle_create_lesson:create_lesson_outputs")
            print(traceback.format_exc())
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"서버에서 오디오 처리 중 예기치 않은 오류가 발생했습니다: {exc}",
            )
            return
        finally:
            try:
                cleanup_temporary_audio_inputs(audio_files)
            except Exception:
                print("Unexpected error in handle_create_lesson:cleanup_temporary_audio_inputs")
                print(traceback.format_exc())

        lesson_id = uuid.uuid4().hex[:12]
        now = utc_now()
        student_slug = self.student_slug(student)

        lesson = enrich_lesson_record(
            {
                "id": lesson_id,
                "student_slug": student_slug or "",
                "lesson_date": lesson_date,
                "article_title": generated["resolved_article_title"],
                "article_url": article_url,
                "article_text": article_text,
                "note": note,
                "tone_samples": tone_samples,
                "audio_file_paths": [],
                "original_audio_names": original_filenames,
                "transcript_text": generated["transcript_text"],
                "transcript_origin": generated["transcript_origin"],
                "generation_source": generated["generation_source"],
                "quality_reviewed": generated.get("quality_reviewed", False),
                "summary_text": generated["summary_text"],
                "summary_points": generated["summary_points"],
                "speaker_turns": generated["speaker_turns"],
                "concept_cards": generated["concept_cards"],
                "dialogue_summary": generated["dialogue_summary"],
                "lesson_headline": generated["lesson_headline"],
                "student_summary": generated["student_summary"],
                "notion_exports": generated["notion_exports"],
                "status": "complete",
                "created_at": now,
                "updated_at": now,
            }
        )

        try:
            create_lesson(lesson, student_slug=student_slug)
            if student_slug:
                touch_student(student_slug)
        except Exception as exc:
            print("Unexpected error in handle_create_lesson:create_lesson")
            print(traceback.format_exc())
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"서버에 기록을 저장하는 중 오류가 발생했습니다: {exc}",
            )
            return
        self.send_json({"lesson": lesson}, status=HTTPStatus.CREATED)

    def handle_regenerate_lesson(self, lesson_id: str, student: dict[str, Any] | None) -> None:
        student_slug = self.student_slug(student)
        lesson = get_lesson(lesson_id, student_slug=student_slug)
        if lesson is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
            return

        lesson = enrich_lesson_record(lesson)

        try:
            generated = create_lesson_outputs(
                lesson_date=lesson.get("lesson_date", ""),
                article_title=lesson.get("article_title", ""),
                article_url=lesson.get("article_url", ""),
                article_text=lesson.get("article_text", ""),
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
                "student_slug": student_slug or lesson.get("student_slug", ""),
                "article_title": generated["resolved_article_title"],
                "article_url": generated.get("article_url", lesson.get("article_url", "")),
                "article_text": generated.get("article_text", lesson.get("article_text", "")),
                "transcript_text": generated["transcript_text"],
                "transcript_origin": generated["transcript_origin"],
                "generation_source": generated["generation_source"],
                "quality_reviewed": generated.get("quality_reviewed", False),
                "summary_text": generated["summary_text"],
                "summary_points": generated["summary_points"],
                "speaker_turns": generated["speaker_turns"],
                "concept_cards": generated["concept_cards"],
                "dialogue_summary": generated["dialogue_summary"],
                "lesson_headline": generated["lesson_headline"],
                "student_summary": generated["student_summary"],
                "notion_exports": generated["notion_exports"],
                "updated_at": utc_now(),
            }
        )
        updated = update_lesson(lesson_id, updated_record, student_slug=student_slug)
        if student_slug:
            touch_student(student_slug)
        self.send_json({"lesson": updated})

    def handle_update_lesson(self, lesson_id: str, student: dict[str, Any] | None) -> None:
        student_slug = self.student_slug(student)
        lesson = get_lesson(lesson_id, student_slug=student_slug)
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
                "student_slug": student_slug or lesson.get("student_slug", ""),
                "article_title": payload.get("article_title", lesson.get("article_title", "")),
                "article_url": payload.get("article_url", lesson.get("article_url", "")),
                "article_text": payload.get("article_text", lesson.get("article_text", "")),
                "lesson_headline": payload.get("lesson_headline", lesson.get("lesson_headline", "")),
                "summary_text": payload.get("summary_text", lesson.get("summary_text", "")),
                "summary_points": payload.get("summary_points", lesson.get("summary_points", [])),
                "concept_cards": payload.get("concept_cards", lesson.get("concept_cards", [])),
                "student_summary": payload.get("student_summary", lesson.get("student_summary", {})),
                "dialogue_summary": payload.get("dialogue_summary", lesson.get("dialogue_summary", "")),
                "updated_at": utc_now(),
            }
        )
        updated = update_lesson(lesson_id, merged, student_slug=student_slug)
        if student_slug:
            touch_student(student_slug)
        self.send_json({"lesson": updated})

    def handle_delete_lesson(self, lesson_id: str, student: dict[str, Any] | None) -> None:
        student_slug = self.student_slug(student)
        deleted = delete_lesson(lesson_id, student_slug=student_slug)
        if not deleted:
            self.send_error_json(HTTPStatus.NOT_FOUND, "기록을 찾지 못했습니다.")
            return

        if student_slug:
            touch_student(student_slug)
        self.send_json({"ok": True, "deleted_id": lesson_id})

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
            "student_slug": lesson.get("student_slug", ""),
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

    def send_binary(
        self,
        body: bytes,
        *,
        content_type: str,
        filename: str | None = None,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status=status)


def normalize_text_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def normalize_text_value(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    return normalize_text_lines(str(raw_value or ""))


def normalize_audio_refs(raw_refs: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(raw_refs, list):
        return normalized

    for item in raw_refs:
        if not isinstance(item, dict):
            continue

        blob_pathname = str(item.get("pathname") or item.get("blob_pathname") or "").strip()
        filename = str(item.get("filename") or item.get("original_name") or "").strip()
        content_type = str(item.get("content_type") or item.get("contentType") or "").strip()
        if not blob_pathname:
            continue

        normalized.append(
            {
                "filename": filename or Path(blob_pathname).name,
                "content_type": content_type or mimetypes.guess_type(blob_pathname)[0] or "application/octet-stream",
                "blob_pathname": blob_pathname,
            }
        )

    return normalized


def parse_checkbox(value: str) -> bool:
    return value.lower() in {"1", "true", "on", "yes"}


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0].strip() if values else ""


def extract_student_slug_from_app_path(path: str) -> str:
    normalized_path = unquote(str(path or "").strip())
    if not normalized_path.startswith("/s/"):
        return ""

    tail = normalized_path.removeprefix("/s/").strip("/")
    if not tail or "/" in tail:
        return ""
    return normalize_student_slug(tail)


def extract_student_slug_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    return extract_student_slug_from_app_path(parsed.path)


def build_student_path(student_slug: str) -> str:
    normalized_slug = normalize_student_slug(student_slug)
    if not normalized_slug:
        return "/"
    return f"/s/{normalized_slug}"


def generate_student_slug(student_name: str) -> str:
    base = normalize_student_slug(student_name)
    if not base:
        base = "student"
    return f"{base}-{uuid.uuid4().hex[:5]}"


def derive_progress_status(*, latest_lesson_date: str, lesson_count: int) -> tuple[str, str]:
    if lesson_count <= 0:
        return ("not_started", "아직 시작 안 함")

    parsed_date = parse_lesson_date(latest_lesson_date)
    if parsed_date is None:
        return ("in_progress", "기록 있음")

    today = datetime.now().date()
    days_ago = (today - parsed_date).days
    if days_ago <= 0:
        return ("submitted_today", "오늘 제출")
    if days_ago <= 7:
        return ("active_recently", "최근 7일 내 제출")
    return ("needs_attention", "확인 필요")


def parse_lesson_date(value: str) -> datetime.date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_local_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def build_network_url(port: int) -> str:
    lan_ip = discover_lan_ip()
    if not lan_ip:
        return ""
    return f"http://{lan_ip}:{port}"


def discover_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
            if candidate and not candidate.startswith("127."):
                return candidate
    except OSError:
        pass

    try:
        candidate = socket.gethostbyname(socket.gethostname())
    except OSError:
        return ""

    return candidate if candidate and not candidate.startswith("127.") else ""


def run() -> None:
    ensure_storage()
    os.chdir(ROOT_DIR)
    server = ThreadingHTTPServer((HOST, PORT), LessonJournalHandler)
    print("Reading Note App running.")
    print(f"Local: {build_local_url(PORT)}")
    network_url = build_network_url(PORT)
    if network_url:
        print(f"Same Wi-Fi: {network_url}")
    server.serve_forever()
