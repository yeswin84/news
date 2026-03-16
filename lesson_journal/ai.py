from __future__ import annotations

import json
import mimetypes
import re
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_TRANSCRIBE_MODEL


class AIProcessingError(RuntimeError):
    """Raised when AI processing cannot be completed."""


def create_lesson_outputs(
    *,
    lesson_date: str,
    article_title: str,
    note: str,
    tone_samples: list[str],
    manual_transcript: str,
    audio_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    transcript_text = manual_transcript.strip()
    transcript_origin = "manual_text" if transcript_text else "api_audio"

    if not transcript_text and audio_inputs:
        transcript_text = transcribe_audio_files(audio_inputs)

    if not transcript_text:
        raise AIProcessingError("전사문 또는 음성 파일이 필요합니다.")

    generated = None
    generation_source = "fallback"

    if OPENAI_API_KEY:
        try:
            generated = generate_structured_record(
                lesson_date=lesson_date,
                article_title=article_title,
                note=note,
                tone_samples=tone_samples,
                transcript_text=transcript_text,
            )
            generation_source = "openai"
        except AIProcessingError:
            generated = None

    if generated is None:
        generated = fallback_generate_record(
            lesson_date=lesson_date,
            article_title=article_title,
            note=note,
            tone_samples=tone_samples,
            transcript_text=transcript_text,
        )

    resolved_article_title = (
        article_title.strip()
        or generated.get("recommended_title", "").strip()
        or infer_title_from_text(transcript_text)
    )
    lesson_headline = (
        generated.get("lesson_headline", "").strip()
        or build_lesson_headline(
            article_title=resolved_article_title,
            dialogue_summary=generated.get("dialogue_summary", ""),
            student_summary=generated.get("student_summary", {}),
        )
    )

    generated["resolved_article_title"] = resolved_article_title
    generated["lesson_headline"] = lesson_headline
    generated["notion_exports"] = build_notion_exports(
        lesson_date=lesson_date,
        article_title=resolved_article_title,
        lesson_headline=lesson_headline,
        dialogue_summary=generated.get("dialogue_summary", ""),
        student_summary=generated.get("student_summary", {}),
        parent_summary=generated.get("parent_summary", {}),
    )
    generated["transcript_text"] = transcript_text
    generated["transcript_origin"] = transcript_origin
    generated["generation_source"] = generation_source
    return generated


def enrich_lesson_record(record: dict[str, Any]) -> dict[str, Any]:
    lesson = dict(record)

    if "audio_file_paths" not in lesson:
        old_path = lesson.get("audio_file_path")
        lesson["audio_file_paths"] = [old_path] if old_path else []

    if "original_audio_names" not in lesson:
        old_name = lesson.get("original_audio_name")
        lesson["original_audio_names"] = [old_name] if old_name else []

    lesson["audio_file_count"] = max(
        len(lesson.get("original_audio_names", [])),
        len(lesson.get("audio_file_paths", [])),
    )

    article_title = (
        lesson.get("article_title", "").strip()
        or lesson.get("parent_summary", {}).get("article_topic", "").strip()
        or infer_title_from_text(lesson.get("transcript_text", ""))
    )
    lesson_headline = (
        lesson.get("lesson_headline", "").strip()
        or build_lesson_headline(
            article_title=article_title,
            dialogue_summary=lesson.get("dialogue_summary", ""),
            student_summary=lesson.get("student_summary", {}),
        )
    )

    lesson["article_title"] = article_title
    lesson["lesson_headline"] = lesson_headline
    lesson["notion_exports"] = build_notion_exports(
        lesson_date=lesson.get("lesson_date", ""),
        article_title=article_title,
        lesson_headline=lesson_headline,
        dialogue_summary=lesson.get("dialogue_summary", ""),
        student_summary=lesson.get("student_summary", {}),
        parent_summary=lesson.get("parent_summary", {}),
    )
    return lesson


def transcribe_audio_files(audio_inputs: list[dict[str, Any]]) -> str:
    transcripts: list[str] = []
    total = len(audio_inputs)

    for index, audio_input in enumerate(audio_inputs, start=1):
        transcript = transcribe_audio(audio_input)
        file_name = audio_input.get("filename") or f"audio-{index}"
        if total == 1:
            transcripts.append(transcript)
        else:
            transcripts.append(f"[음성 {index}: {file_name}]\n{transcript}")

    return "\n\n".join(part.strip() for part in transcripts if part.strip()).strip()


def transcribe_audio(audio_input: dict[str, Any]) -> str:
    if not OPENAI_API_KEY:
        raise AIProcessingError("음성 자동 전사를 사용하려면 OPENAI_API_KEY가 필요합니다.")

    file_name = audio_input.get("filename") or f"audio-{uuid.uuid4().hex}.bin"
    mime_type = audio_input.get("content_type") or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_bytes = audio_input.get("content") or b""
    content_type, body = build_multipart_form(
        fields={
            "model": OPENAI_TRANSCRIBE_MODEL,
            "language": "ko",
            "temperature": "0",
        },
        files=[
            {
                "field_name": "file",
                "filename": file_name,
                "content_type": mime_type,
                "content": file_bytes,
            }
        ],
    )

    request = Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": content_type,
        },
    )

    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AIProcessingError(f"음성 전사 API 호출이 실패했습니다: {detail}") from exc
    except URLError as exc:
        raise AIProcessingError(f"음성 전사 API 연결에 실패했습니다: {exc}") from exc

    text = payload.get("text", "").strip()
    if not text:
        raise AIProcessingError("전사 결과를 받지 못했습니다.")
    return text


def generate_structured_record(
    *,
    lesson_date: str,
    article_title: str,
    note: str,
    tone_samples: list[str],
    transcript_text: str,
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise AIProcessingError("텍스트 생성을 사용하려면 OPENAI_API_KEY가 필요합니다.")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recommended_title": {"type": "string"},
            "lesson_headline": {"type": "string"},
            "dialogue_summary": {"type": "string"},
            "speaker_turns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "speaker": {"type": "string", "enum": ["teacher", "student"]},
                        "text": {"type": "string"},
                    },
                    "required": ["speaker", "text"],
                },
            },
            "student_summary": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "topic": {"type": "string"},
                    "conversation": {"type": "string"},
                    "student_thought": {"type": "string"},
                    "new_learning": {"type": "string"},
                    "difficult_part": {"type": "string"},
                    "one_line_feeling": {"type": "string"},
                },
                "required": [
                    "topic",
                    "conversation",
                    "student_thought",
                    "new_learning",
                    "difficult_part",
                    "one_line_feeling",
                ],
            },
            "parent_summary": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "lesson_date": {"type": "string"},
                    "article_topic": {"type": "string"},
                    "core_content": {"type": "string"},
                    "student_understanding": {"type": "string"},
                    "student_opinion": {"type": "string"},
                    "strengths": {"type": "string"},
                    "needs_support": {"type": "string"},
                    "next_study_suggestion": {"type": "string"},
                },
                "required": [
                    "lesson_date",
                    "article_topic",
                    "core_content",
                    "student_understanding",
                    "student_opinion",
                    "strengths",
                    "needs_support",
                    "next_study_suggestion",
                ],
            },
        },
        "required": [
            "recommended_title",
            "lesson_headline",
            "dialogue_summary",
            "speaker_turns",
            "student_summary",
            "parent_summary",
        ],
    }

    tone_block = "\n".join(f"- {sample}" for sample in tone_samples if sample.strip()) or "- 말투 샘플 없음"
    user_prompt = f"""
수업 날짜: {lesson_date or "미입력"}
기사 제목: {article_title or "비워둠 - 전사문을 보고 추론해줘"}
추가 메모: {note or "없음"}

학생 말투 샘플:
{tone_block}

전사문:
{transcript_text}
""".strip()

    payload = {
        "model": OPENAI_TEXT_MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "너는 중학교 2학년 학생의 신문 읽기 수업을 정리하는 도우미다. "
                            "반드시 전사문에 근거해서만 작성하고 없는 사실을 추가하지 마라. "
                            "사용자는 음성 파일만 올려도 바로 결과물을 받고 싶어 한다. "
                            "recommended_title은 기사 제목이 없을 때도 자연스럽게 붙일 수 있는 짧은 제목으로 작성해라. "
                            "lesson_headline은 노션 상단에 들어갈 한 문장 요약으로, 어색하지 않고 그럴듯하게 써라. "
                            "student_summary는 중학교 2학년 학생이 직접 쓴 것처럼 솔직하고 자연스럽게, 각 항목당 1~3문장으로 작성해라. "
                            "지나치게 모범답안 같거나 성인처럼 말하지 마라. "
                            "parent_summary는 관찰 중심으로 간단하고 명확하게 정리해라. "
                            "speaker_turns는 teacher/student만 사용하고 짧은 핵심 문장만 남겨라. "
                            "반드시 JSON만 반환해라."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lesson_record",
                "strict": True,
                "schema": schema,
            }
        },
    }

    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=120) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AIProcessingError(f"요약 생성 API 호출이 실패했습니다: {detail}") from exc
    except URLError as exc:
        raise AIProcessingError(f"요약 생성 API 연결에 실패했습니다: {exc}") from exc

    output_text = extract_response_text(raw_payload)
    if not output_text:
        raise AIProcessingError("요약 생성 결과를 받지 못했습니다.")

    try:
        structured = json.loads(strip_code_fence(output_text))
    except json.JSONDecodeError as exc:
        raise AIProcessingError("요약 생성 결과가 JSON 형식이 아닙니다.") from exc
    return structured


def build_multipart_form(fields: dict[str, str], files: list[dict[str, Any]]) -> tuple[str, bytes]:
    boundary = f"----LessonJournal{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    for file_info in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{file_info["field_name"]}"; '
                    f'filename="{file_info["filename"]}"\r\n'
                ).encode("utf-8"),
                f'Content-Type: {file_info["content_type"]}\r\n\r\n'.encode("utf-8"),
                file_info["content"],
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return f"multipart/form-data; boundary={boundary}", b"".join(chunks)


def extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text_value = content.get("text")
            if isinstance(text_value, str):
                texts.append(text_value)
            elif isinstance(text_value, dict):
                value = text_value.get("value")
                if isinstance(value, str):
                    texts.append(value)
            alt_value = content.get("output_text")
            if isinstance(alt_value, str):
                texts.append(alt_value)

    return "\n".join(texts).strip()


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def fallback_generate_record(
    *,
    lesson_date: str,
    article_title: str,
    note: str,
    tone_samples: list[str],
    transcript_text: str,
) -> dict[str, Any]:
    speaker_turns = parse_speaker_turns(transcript_text)
    student_turns = [turn["text"] for turn in speaker_turns if turn["speaker"] == "student"]
    teacher_turns = [turn["text"] for turn in speaker_turns if turn["speaker"] == "teacher"]
    transcript_sentences = split_sentences(transcript_text)

    recommended_title = article_title.strip() or infer_title_from_text(transcript_text)
    topic = (
        f"{recommended_title}에 관한 기사와 수업 이야기였다."
        if recommended_title
        else "오늘 읽은 기사 내용을 중심으로 이야기했다."
    )

    conversation = first_non_empty(
        join_sentences(teacher_turns[:2]),
        join_sentences(transcript_sentences[:2]),
        "기사 내용을 읽고 왜 그런 일이 생기는지와 내 생각을 같이 이야기했다.",
    )

    student_thought = first_non_empty(
        pick_opinion_sentence(student_turns),
        join_sentences(student_turns[:2]),
        "내 경험이랑 연결해서 생각해 본 점을 말해봤다.",
    )

    new_learning = first_non_empty(
        pick_learning_sentence(transcript_sentences),
        "기사 내용이 생활 습관이랑 연결될 수 있다는 점이 기억에 남았다.",
    )

    difficult_part = first_non_empty(
        pick_difficult_sentence(student_turns + transcript_sentences),
        "숫자나 근거가 나오는 부분을 바로 이해하는 건 조금 헷갈릴 수 있었다.",
    )

    one_line_feeling = build_one_line_feeling(recommended_title, transcript_text, tone_samples)
    dialogue_summary = first_non_empty(
        join_sentences(transcript_sentences[:2]),
        one_line_feeling,
        "수업 내용을 짧게 정리했다.",
    )
    lesson_headline = build_lesson_headline(
        article_title=recommended_title,
        dialogue_summary=dialogue_summary,
        student_summary={
            "student_thought": student_thought,
            "one_line_feeling": one_line_feeling,
        },
    )

    return {
        "recommended_title": recommended_title,
        "lesson_headline": lesson_headline,
        "dialogue_summary": dialogue_summary,
        "speaker_turns": speaker_turns,
        "student_summary": {
            "topic": topic,
            "conversation": conversation,
            "student_thought": student_thought,
            "new_learning": new_learning,
            "difficult_part": difficult_part,
            "one_line_feeling": one_line_feeling,
        },
        "parent_summary": {
            "lesson_date": lesson_date,
            "article_topic": recommended_title,
            "core_content": join_sentences(transcript_sentences[:3])
            or "기사 주제를 읽고 학생의 의견을 말해보는 수업을 진행함",
            "student_understanding": build_parent_understanding(student_turns, transcript_sentences),
            "student_opinion": student_thought,
            "strengths": build_strength_sentence(student_turns),
            "needs_support": difficult_part,
            "next_study_suggestion": build_next_study_suggestion(transcript_text, recommended_title, note),
        },
    }


def build_notion_exports(
    *,
    lesson_date: str,
    article_title: str,
    lesson_headline: str,
    dialogue_summary: str,
    student_summary: dict[str, str],
    parent_summary: dict[str, str],
) -> dict[str, str]:
    title = article_title.strip() or "오늘 수업 기록"
    headline = lesson_headline.strip() or dialogue_summary.strip() or "오늘 수업 내용을 정리했다."

    student_markdown = "\n".join(
        [
            f"# 학생 기록 | {title}",
            "",
            f"- 수업 날짜: {lesson_date or '미입력'}",
            f"- 오늘 한 줄 느낌: {student_summary.get('one_line_feeling', '').strip() or '기록 없음'}",
            "",
            "## 오늘 읽은 기사 주제",
            student_summary.get("topic", "").strip() or "기록 없음",
            "",
            "## 선생님이랑 나눈 이야기",
            student_summary.get("conversation", "").strip() or "기록 없음",
            "",
            "## 내가 말한 생각",
            student_summary.get("student_thought", "").strip() or "기록 없음",
            "",
            "## 새로 알게 된 점",
            student_summary.get("new_learning", "").strip() or "기록 없음",
            "",
            "## 어려웠던 부분",
            student_summary.get("difficult_part", "").strip() or "기록 없음",
            "",
            "## 오늘 한 줄 느낌",
            student_summary.get("one_line_feeling", "").strip() or "기록 없음",
        ]
    ).strip()

    parent_markdown = "\n".join(
        [
            f"# 보호자 기록 | {title}",
            "",
            f"- 수업 날짜: {parent_summary.get('lesson_date', '').strip() or lesson_date or '미입력'}",
            f"- 기사 주제: {parent_summary.get('article_topic', '').strip() or title}",
            "",
            "## 수업에서 다룬 핵심 내용",
            parent_summary.get("core_content", "").strip() or "기록 없음",
            "",
            "## 학생이 이해한 내용",
            parent_summary.get("student_understanding", "").strip() or "기록 없음",
            "",
            "## 학생이 표현한 의견",
            parent_summary.get("student_opinion", "").strip() or "기록 없음",
            "",
            "## 잘한 점",
            parent_summary.get("strengths", "").strip() or "기록 없음",
            "",
            "## 보완이 필요한 점",
            parent_summary.get("needs_support", "").strip() or "기록 없음",
            "",
            "## 다음 학습 제안",
            parent_summary.get("next_study_suggestion", "").strip() or "기록 없음",
        ]
    ).strip()

    combined_markdown = "\n".join(
        [
            f"# {title}",
            "",
            f"> {headline}",
            "",
            f"- 수업 날짜: {lesson_date or '미입력'}",
            f"- 한 줄 요약: {dialogue_summary.strip() or headline}",
            "",
            "## 학생 기록",
            f"### 오늘 읽은 기사 주제\n{student_summary.get('topic', '').strip() or '기록 없음'}",
            "",
            f"### 선생님이랑 나눈 이야기\n{student_summary.get('conversation', '').strip() or '기록 없음'}",
            "",
            f"### 내가 말한 생각\n{student_summary.get('student_thought', '').strip() or '기록 없음'}",
            "",
            f"### 새로 알게 된 점\n{student_summary.get('new_learning', '').strip() or '기록 없음'}",
            "",
            f"### 어려웠던 부분\n{student_summary.get('difficult_part', '').strip() or '기록 없음'}",
            "",
            f"### 오늘 한 줄 느낌\n{student_summary.get('one_line_feeling', '').strip() or '기록 없음'}",
            "",
            "## 보호자 기록",
            f"- 수업에서 다룬 핵심 내용: {parent_summary.get('core_content', '').strip() or '기록 없음'}",
            f"- 학생이 이해한 내용: {parent_summary.get('student_understanding', '').strip() or '기록 없음'}",
            f"- 학생이 표현한 의견: {parent_summary.get('student_opinion', '').strip() or '기록 없음'}",
            f"- 잘한 점: {parent_summary.get('strengths', '').strip() or '기록 없음'}",
            f"- 보완이 필요한 점: {parent_summary.get('needs_support', '').strip() or '기록 없음'}",
            f"- 다음 학습 제안: {parent_summary.get('next_study_suggestion', '').strip() or '기록 없음'}",
        ]
    ).strip()

    return {
        "student_markdown": student_markdown,
        "parent_markdown": parent_markdown,
        "combined_markdown": combined_markdown,
    }


def parse_speaker_turns(transcript_text: str) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    speaker_patterns = [
        ("student", r"^(학생|나|student)\s*[:：-]\s*(.+)$"),
        ("teacher", r"^(선생님|teacher|tutor)\s*[:：-]\s*(.+)$"),
    ]

    for raw_line in transcript_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = None
        for speaker, pattern in speaker_patterns:
            matched = re.match(pattern, line, flags=re.IGNORECASE)
            if matched:
                turns.append({"speaker": speaker, "text": matched.group(2).strip()})
                break

    if turns:
        return turns

    sentences = split_sentences(transcript_text)
    if not sentences:
        return [{"speaker": "student", "text": transcript_text.strip()}]

    alternating: list[dict[str, str]] = []
    for index, sentence in enumerate(sentences[:8]):
        speaker = "teacher" if index % 2 == 0 else "student"
        alternating.append({"speaker": speaker, "text": sentence})
    return alternating


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?<=다\.)\s+|[\r\n]+", normalized)
    return [part.strip() for part in parts if part.strip()]


def join_sentences(sentences: list[str]) -> str:
    return " ".join(sentence.strip() for sentence in sentences if sentence.strip()).strip()


def first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def infer_title_from_text(transcript_text: str) -> str:
    sentences = split_sentences(transcript_text)
    if not sentences:
        return "오늘 수업 기사"

    cleaned = re.sub(r"^(학생|선생님|teacher|student)\s*[:：-]\s*", "", sentences[0], flags=re.IGNORECASE)
    cleaned = re.sub(r"\[[^\]]+\]", "", cleaned).strip()
    if 6 <= len(cleaned) <= 28:
        return cleaned
    if cleaned:
        return f"{cleaned[:18].strip()} 관련 기사"
    return "오늘 수업 기사"


def build_lesson_headline(
    *,
    article_title: str,
    dialogue_summary: str,
    student_summary: dict[str, str],
) -> str:
    one_line = student_summary.get("one_line_feeling", "").strip()
    student_thought = student_summary.get("student_thought", "").strip()

    if one_line:
        return one_line
    if dialogue_summary.strip():
        return dialogue_summary.strip()
    if student_thought:
        return student_thought
    if article_title:
        return f"{article_title} 이야기를 내 경험과 연결해서 생각해본 수업이었다."
    return "오늘 수업 내용을 바탕으로 내 생각을 정리해본 시간이었다."


def pick_opinion_sentence(sentences: list[str]) -> str:
    keywords = ["생각", "의견", "느낌", "같다", "나는", "제가", "내가", "공감", "맞는 것"]
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence
    return ""


def pick_learning_sentence(sentences: list[str]) -> str:
    keywords = ["알게", "배웠", "처음", "이해", "깨달", "영향", "기억에 남"]
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence
    if sentences:
        return f"기사 내용을 이야기하면서 {sentences[0][:60].rstrip()} 부분이 기억에 남았다."
    return ""


def pick_difficult_sentence(sentences: list[str]) -> str:
    keywords = ["어려", "헷갈", "잘 모르", "모르겠", "복잡", "통계", "숫자"]
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence
    return ""


def build_one_line_feeling(article_title: str, transcript_text: str, tone_samples: list[str]) -> str:
    if "공감" in transcript_text:
        return "내 경험이랑 비슷한 부분이 있어서 생각보다 공감되는 수업이었다."
    if "어렵" in transcript_text or "헷갈" in transcript_text:
        return "완전히 쉽지는 않았지만 생각할 게 많았던 수업이었다."
    if article_title:
        return f"{article_title} 이야기가 생각보다 내 생활이랑 가까워서 기억에 남았다."
    if tone_samples:
        return "내가 직접 말한 생각이 정리되니까 수업 내용이 더 또렷하게 남는 느낌이었다."
    return "짧게 이야기했는데도 다시 생각해볼 점이 남는 수업이었다."


def build_parent_understanding(student_turns: list[str], transcript_sentences: list[str]) -> str:
    if student_turns:
        return "학생이 자신의 경험과 기사 내용을 연결해 의견을 말하려는 흐름이 보였음"
    if transcript_sentences:
        return "기사의 큰 주제를 따라가며 핵심 내용을 이해하려는 흐름이 확인됨"
    return "학생 이해도 확인을 위한 추가 대화가 필요함"


def build_strength_sentence(student_turns: list[str]) -> str:
    if len(student_turns) >= 2:
        return "짧은 답변에 그치지 않고 자신의 생각을 덧붙여 말한 점이 좋았음"
    if student_turns:
        return "기사와 관련된 자신의 경험이나 느낌을 말로 표현한 점이 좋았음"
    return "수업 내용에 반응하며 핵심을 따라가려는 태도가 보였음"


def build_next_study_suggestion(transcript_text: str, article_title: str, note: str) -> str:
    if any(keyword in transcript_text for keyword in ["통계", "숫자", "자료"]):
        return "짧은 통계 자료를 보고 핵심 의미를 한 문장으로 설명하는 연습을 권장함"
    if "의견" in transcript_text or "생각" in transcript_text:
        return "기사 핵심 주장에 대한 찬반 이유를 두 문장으로 말하는 연습을 권장함"
    if article_title:
        return f"{article_title}와 비슷한 짧은 기사 한 편을 읽고 핵심을 말로 정리해보는 것을 권장함"
    if note:
        return "수업 메모를 바탕으로 핵심 낱말을 먼저 정리한 뒤 말로 설명하는 연습을 권장함"
    return "짧은 기사 한 편을 읽고 핵심 내용과 자기 생각을 나눠서 말해보는 연습을 권장함"
