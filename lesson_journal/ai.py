from __future__ import annotations

import json
import mimetypes
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import OPENAI_API_KEY, OPENAI_TEXT_MODEL, OPENAI_TRANSCRIBE_MODEL
from .storage import load_audio_input_content


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
    article_url: str = "",
    article_text: str = "",
) -> dict[str, Any]:
    transcript_text = manual_transcript.strip()
    article_url = article_url.strip()
    article_text = article_text.strip()
    transcript_origin = "manual_text" if transcript_text else "api_audio"

    if not transcript_text and audio_inputs:
        transcript_text = transcribe_audio_files_parallel(audio_inputs)

    if not transcript_text and article_text:
        transcript_text = article_text
        transcript_origin = "article_text"

    if not transcript_text:
        raise AIProcessingError("전사문 또는 음성 파일이 필요합니다.")

    generated = None
    generation_source = "fallback"

    if OPENAI_API_KEY:
        try:
            generated = generate_structured_record(
                lesson_date=lesson_date,
                article_title=article_title,
                article_url=article_url,
                article_text=article_text,
                note=note,
                tone_samples=tone_samples,
                transcript_text=transcript_text,
            )
            generation_source = "openai"
            try:
                generated = review_structured_record(
                    lesson_date=lesson_date,
                    article_title=article_title,
                    article_url=article_url,
                    article_text=article_text,
                    note=note,
                    tone_samples=tone_samples,
                    transcript_text=transcript_text,
                    draft_record=generated,
                )
                generation_source = "openai_reviewed"
            except AIProcessingError:
                pass
        except AIProcessingError:
            generated = None

    if generated is None:
        generated = fallback_generate_record(
            lesson_date=lesson_date,
            article_title=article_title,
            article_url=article_url,
            article_text=article_text,
            note=note,
            tone_samples=tone_samples,
            transcript_text=transcript_text,
        )

    resolved_article_title = (
        article_title.strip()
        or generated.get("recommended_title", "").strip()
        or infer_title_from_text(article_text or transcript_text)
    )
    summary_text = generated.get("summary_text", "").strip() or generated.get("dialogue_summary", "").strip()
    lesson_headline = (
        generated.get("lesson_headline", "").strip()
        or build_lesson_headline(
            article_title=resolved_article_title,
            dialogue_summary=generated.get("dialogue_summary", ""),
            student_summary=generated.get("student_summary", {}),
        )
    )
    summary_points = normalize_summary_points(generated.get("summary_points") or [])
    if not summary_points:
        summary_points = build_fallback_summary_points(
            transcript_text=combine_source_texts(article_text, transcript_text),
            article_title=resolved_article_title,
            summary_text=summary_text,
            student_summary=generated.get("student_summary", {}) or {},
        )

    generated["resolved_article_title"] = resolved_article_title
    generated["summary_text"] = summary_text
    generated["lesson_headline"] = lesson_headline
    generated["summary_points"] = summary_points
    generated = normalize_student_voice_record(generated)
    summary_text = generated.get("summary_text", "").strip()
    lesson_headline = generated.get("lesson_headline", "").strip()
    summary_points = normalize_summary_points(generated.get("summary_points") or [])
    student_summary = dict(generated.get("student_summary", {}) or {})
    concept_cards = normalize_concept_cards(generated.get("concept_cards") or [])
    generated["summary_text"] = summary_text
    generated["lesson_headline"] = lesson_headline
    generated["summary_points"] = summary_points
    generated["student_summary"] = student_summary
    generated["concept_cards"] = concept_cards
    generated["notion_exports"] = build_notion_exports(
        lesson_date=lesson_date,
        article_title=resolved_article_title,
        lesson_headline=lesson_headline,
        summary_text=summary_text,
        dialogue_summary=generated.get("dialogue_summary", ""),
        summary_points=summary_points,
        student_summary=student_summary,
        concept_cards=concept_cards,
        transcript_text=transcript_text,
    )
    generated["transcript_text"] = transcript_text
    generated["transcript_origin"] = transcript_origin
    generated["generation_source"] = generation_source
    generated["article_url"] = article_url
    generated["article_text"] = article_text
    generated["quality_reviewed"] = generation_source == "openai_reviewed"
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
    lesson["article_url"] = str(lesson.get("article_url", "") or "").strip()
    lesson["article_text"] = str(lesson.get("article_text", "") or "").strip()
    student_summary = dict(lesson.get("student_summary", {}) or {})
    parent_summary = dict(lesson.get("parent_summary", {}) or {})
    if "understanding" not in student_summary:
        student_summary["understanding"] = (
            student_summary.get("conversation", "").strip()
            or student_summary.get("new_learning", "").strip()
            or parent_summary.get("student_understanding", "").strip()
        )
    if "thinking_point" not in student_summary:
        student_summary["thinking_point"] = parent_summary.get("next_study_suggestion", "").strip()
    concept_cards = normalize_concept_cards(lesson.get("concept_cards") or [])
    if not concept_cards:
        concept_cards = build_fallback_concept_cards(
            transcript_text=combine_source_texts(lesson.get("article_text", ""), lesson.get("transcript_text", "")),
            article_title=lesson.get("article_title", ""),
            summary_text=lesson.get("summary_text", "") or lesson.get("dialogue_summary", ""),
            difficult_part=student_summary.get("difficult_part", ""),
        )
    article_title = (
        lesson.get("article_title", "").strip()
        or parent_summary.get("article_topic", "").strip()
        or infer_title_from_text(lesson.get("article_text", "") or lesson.get("transcript_text", ""))
    )
    summary_text = lesson.get("summary_text", "").strip() or lesson.get("dialogue_summary", "").strip()
    lesson_headline = (
        lesson.get("lesson_headline", "").strip()
        or build_lesson_headline(
            article_title=article_title,
            dialogue_summary=lesson.get("dialogue_summary", ""),
            student_summary=student_summary,
        )
    )
    summary_points = normalize_summary_points(lesson.get("summary_points") or [])
    if not summary_points:
        summary_points = build_fallback_summary_points(
            transcript_text=lesson.get("transcript_text", ""),
            article_title=article_title,
            summary_text=summary_text,
            student_summary=student_summary,
        )

    lesson["article_title"] = article_title
    lesson["summary_text"] = summary_text
    lesson["lesson_headline"] = lesson_headline
    lesson["summary_points"] = summary_points
    lesson["student_summary"] = student_summary
    lesson["concept_cards"] = concept_cards
    lesson = normalize_student_voice_record(lesson)
    summary_text = lesson.get("summary_text", "").strip()
    lesson_headline = lesson.get("lesson_headline", "").strip()
    summary_points = normalize_summary_points(lesson.get("summary_points") or [])
    student_summary = dict(lesson.get("student_summary", {}) or {})
    concept_cards = normalize_concept_cards(lesson.get("concept_cards") or [])
    lesson["summary_text"] = summary_text
    lesson["lesson_headline"] = lesson_headline
    lesson["summary_points"] = summary_points
    lesson["student_summary"] = student_summary
    lesson["concept_cards"] = concept_cards
    lesson.pop("parent_summary", None)
    lesson["notion_exports"] = build_notion_exports(
        lesson_date=lesson.get("lesson_date", ""),
        article_title=article_title,
        lesson_headline=lesson_headline,
        summary_text=summary_text,
        dialogue_summary=lesson.get("dialogue_summary", ""),
        summary_points=summary_points,
        student_summary=student_summary,
        concept_cards=concept_cards,
        transcript_text=lesson.get("transcript_text", ""),
    )
    return lesson


def transcribe_audio_files_parallel(audio_inputs: list[dict[str, Any]]) -> str:
    total = len(audio_inputs)
    if total == 0:
        return ""

    if total == 1:
        return transcribe_audio_files(audio_inputs)

    transcripts_by_index: dict[int, str] = {}
    max_workers = min(3, total)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(transcribe_audio, audio_input): index
            for index, audio_input in enumerate(audio_inputs, start=1)
        }
        for future in as_completed(futures):
            index = futures[future]
            transcripts_by_index[index] = future.result()

    transcripts: list[str] = []
    for index, audio_input in enumerate(audio_inputs, start=1):
        transcript = transcripts_by_index.get(index, "")
        file_name = audio_input.get("filename") or f"audio-{index}"
        transcripts.append(f"[음성 {index}: {file_name}]\n{transcript}")

    return "\n\n".join(part.strip() for part in transcripts if part.strip()).strip()


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

    hydrated_input = load_audio_input_content(audio_input)
    file_name = hydrated_input.get("filename") or f"audio-{uuid.uuid4().hex}.bin"
    mime_type = hydrated_input.get("content_type") or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_bytes = hydrated_input.get("content") or b""
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


def compact_source_text(text: str, limit: int = 12000) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(normalized) <= limit:
        return normalized

    half = max(1000, limit // 2)
    return f"{normalized[:half].rstrip()}\n\n...[중간 생략]...\n\n{normalized[-half:].lstrip()}"


def combine_source_texts(*texts: str) -> str:
    return "\n\n".join(str(text or "").strip() for text in texts if str(text or "").strip()).strip()


def build_generation_source_block(*, article_url: str, article_text: str, transcript_text: str) -> str:
    article_text = compact_source_text(article_text, limit=14000)
    transcript_text = compact_source_text(transcript_text, limit=16000)
    return f"""
기사 URL:
{article_url or "없음"}

기사 원문:
{article_text or "없음"}

수업/토론 전사문:
{transcript_text or "없음"}
""".strip()


def generate_structured_record(
    *,
    lesson_date: str,
    article_title: str,
    article_url: str,
    article_text: str,
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
            "summary_text": {"type": "string"},
            "dialogue_summary": {"type": "string"},
            "summary_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["title", "detail"],
                },
            },
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
            "concept_cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "term": {"type": "string"},
                        "meaning": {"type": "string"},
                        "related_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "lesson_connection": {"type": "string"},
                    },
                    "required": ["term", "meaning", "related_terms", "lesson_connection"],
                },
            },
            "student_summary": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "topic": {"type": "string"},
                    "understanding": {"type": "string"},
                    "student_thought": {"type": "string"},
                    "difficult_part": {"type": "string"},
                    "thinking_point": {"type": "string"},
                    "one_line_feeling": {"type": "string"},
                },
                "required": [
                    "topic",
                    "understanding",
                    "student_thought",
                    "difficult_part",
                    "thinking_point",
                    "one_line_feeling",
                ],
            },
        },
        "required": [
            "recommended_title",
            "lesson_headline",
            "summary_text",
            "dialogue_summary",
            "summary_points",
            "speaker_turns",
            "concept_cards",
            "student_summary",
        ],
    }

    tone_block = "\n".join(f"- {sample}" for sample in tone_samples if sample.strip()) or "- 말투 샘플 없음"
    source_block = build_generation_source_block(
        article_url=article_url,
        article_text=article_text,
        transcript_text=transcript_text,
    )
    user_prompt = f"""
기록 날짜: {lesson_date or "미입력"}
기사 제목: {article_title or "비워둠 - 전사문을 보고 추론해줘"}
추가 메모: {note or "없음"}

학생 말투 샘플:
{tone_block}

자료:
{source_block}
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
                            "너는 중학생이 읽은 뉴스 기사와 자기 생각을 정리하는 도우미다. "
                            "반드시 제공된 자료에 근거해서만 작성하고 없는 사실을 추가하지 마라. "
                            "단, 기사 원문이 제공되면 기사 원문을 사실 확인의 1차 근거로 삼고 전사문은 학생 반응, 질문, 토론 흐름을 파악하는 근거로 삼아라. "
                            "기사 원문과 전사문이 충돌하면 기사의 사실관계는 기사 원문을 우선하고, 학생이 무엇을 느꼈는지는 전사문을 우선하라. "
                            "기사 원문이 있으면 제목, 핵심 사실, 주요 개념, 관련 용어를 기사 원문에서 더 충실하게 뽑아라. "
                            "기본 상황은 학생이 혼자 기사를 읽고 자신의 이해와 생각을 음성으로 남긴 자기주도형 기록이다. "
                            "전사문에 선생님과의 대화가 섞여 있을 수는 있지만, 결과는 학생의 자기 기록처럼 자연스럽게 정리해라. "
                            "결과 전체는 선생님이 대신 써준 보고서가 아니라 학생이 스스로 복기하며 적은 기록문처럼 보여야 한다. "
                            "절대로 '오늘 수업에서는', '학생은', '함께 배웠다' 같은 교사 요약형 말투를 쓰지 마라. "
                            "summary_text, dialogue_summary, summary_points.detail, concept_cards.lesson_connection, student_summary의 모든 문장은 학생 시점의 기록처럼 써라. "
                            "요약 문장과 설명 문장은 반말이 아니라 가벼운 존댓말로 써라. 예: '~라고 느꼈어요', '~를 알게 됐어요', '~가 아직 조금 헷갈렸어요'. "
                            "가능하면 '저는', '제가', '제 입장에서는' 같은 자기 서술형 표현을 자연스럽게 섞어라. "
                            "다만 모든 문장을 똑같이 시작하지는 말고, 실제 학생이 쓴 것처럼 자연스럽게 변주해라. "
                            "사용자는 음성 파일과 기사 자료를 올리면 바로 결과물을 받고 싶어 한다. "
                            "recommended_title은 기사 제목이 없을 때도 자연스럽게 붙일 수 있는 짧은 제목으로 작성해라. "
                            "lesson_headline은 노션 상단에 들어갈 한 문장 메모로, 학생이 직접 적은 짧은 기록처럼 가벼운 존댓말로 써라. "
                            "summary_text는 학생이 오늘 읽은 기사에서 무엇을 이해했고 무엇이 중요하게 느껴졌는지를 4~6문장으로 충실하게 적어라. "
                            "summary_text 안에서는 기사 내용, 새롭게 연결된 개념, 내 생각이나 느낌이 함께 보이게 하되 headline을 반복하지 마라. "
                            "dialogue_summary는 리스트 카드에서 보일 짧은 한 문장 메모처럼, 가벼운 존댓말로 작성해라. "
                            "summary_points는 summary_text와 다르게 2~4개의 카드형 핵심 포인트를 title, detail 형식으로 정리해라. "
                            "각 summary_points는 기사 주제, 이해한 핵심, 중요하게 본 생각, 더 생각해볼 질문처럼 서로 다른 각도를 담아라. "
                            "concept_cards는 오늘 기사에서 새롭게 알게 된 개념이나 용어를 가능하면 3개 이상 뽑아 term, meaning, related_terms, lesson_connection으로 정리해라. "
                            "related_terms는 전사에 직접 없더라도 기사 이해에 도움되는 관련 용어를 2~4개까지만 붙여도 된다. "
                            "lesson_connection은 왜 내가 이 개념을 같이 기억해두고 싶은지, 오늘 기사 내용과 어떻게 연결해서 이해했는지를 1~2문장으로 설명해라. "
                            "student_summary는 중학교 2학년 학생이 직접 쓴 것처럼 솔직하고 자연스럽게, 각 항목당 1~2문장으로 작성하되 너무 짧지 않게 구체성을 넣어라. "
                            "student_summary.topic은 summary_text를 그대로 줄여 쓰지 말고 학생 입장에서 오늘 읽은 기사 주제를 정리해라. "
                            "student_summary.understanding은 학생이 이번 기록을 통해 실제로 이해한 핵심을 적어라. "
                            "student_summary.student_thought는 학생이 중요하다고 느끼거나 공감한 생각을 적어라. "
                            "student_summary.difficult_part는 아직 조금 헷갈리거나 더 찾아보고 싶은 지점을 적어라. "
                            "student_summary.thinking_point는 숙제가 아니라 학생이 한 번 더 생각해볼 질문이나 포인트로 작성해라. "
                            "지나치게 모범답안 같거나 성인처럼 말하지 마라. "
                            "speaker_turns는 teacher/student만 사용하되, 독백형 전사라면 student만 사용해도 된다. "
                            "선생님이 명확히 등장하지 않으면 teacher를 억지로 만들지 마라. "
                            "출력끼리 중복을 줄여라. summary_text, summary_points, concept_cards, student_summary가 서로 같은 문장을 반복하지 마라. "
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


def review_structured_record(
    *,
    lesson_date: str,
    article_title: str,
    article_url: str,
    article_text: str,
    note: str,
    tone_samples: list[str],
    transcript_text: str,
    draft_record: dict[str, Any],
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise AIProcessingError("품질 검수에는 OPENAI_API_KEY가 필요합니다.")

    source_block = build_generation_source_block(
        article_url=article_url,
        article_text=article_text,
        transcript_text=transcript_text,
    )
    tone_block = "\n".join(f"- {sample}" for sample in tone_samples if sample.strip()) or "- 말투 샘플 없음"
    draft_json = json.dumps(draft_record, ensure_ascii=False, indent=2)
    user_prompt = f"""
기록 날짜: {lesson_date or "미입력"}
기사 제목: {article_title or "비워둠"}
추가 메모: {note or "없음"}

학생 말투 샘플:
{tone_block}

자료:
{source_block}

초안 JSON:
{draft_json}
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
                            "너는 뉴스 읽기 기록의 품질 검수자이자 편집자다. "
                            "입력된 초안 JSON과 자료를 비교해서 같은 JSON 구조로 더 나은 최종본만 반환하라. "
                            "절대 설명문이나 마크다운을 덧붙이지 말고 JSON 객체만 반환하라. "
                            "검수 기준은 다음과 같다. "
                            "첫째, 선생님이 대신 써준 보고서 말투를 학생이 스스로 남긴 기록 말투로 바꾼다. "
                            "둘째, summary_text, summary_points, concept_cards, student_summary가 같은 말을 반복하지 않게 역할을 분리한다. "
                            "summary_text는 기사와 토론의 큰 흐름, summary_points는 핵심 포인트, concept_cards는 개념과 관련 용어, student_summary는 학생의 이해와 반응만 담는다. "
                            "셋째, 기사 원문이 있으면 사실, 인물, 수치, 사건, 개념은 기사 원문을 우선 근거로 삼는다. "
                            "넷째, 전사문은 학생이 흥미를 보인 점, 헷갈린 점, 자신의 의견을 파악하는 근거로 삼는다. "
                            "다섯째, 개념 카드는 가능한 3개 이상 만들고 각 meaning에는 쉬운 설명을, related_terms에는 기사 이해에 도움이 되는 용어 2~4개를, lesson_connection에는 왜 이 개념을 기억하면 좋은지 적는다. "
                            "여섯째, 문장은 가벼운 존댓말로 쓰되 모든 문장을 같은 어미로 끝내지 말고 자연스럽게 변주한다. "
                            "일곱째, 자료에 없는 사실은 만들지 말고, 불확실한 내용은 '더 찾아보고 싶어요'처럼 학생의 다음 생각으로 처리한다. "
                            "반환 JSON의 키는 초안과 동일하게 유지하라."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
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
        raise AIProcessingError(f"품질 검수 API 호출에 실패했습니다: {detail}") from exc
    except URLError as exc:
        raise AIProcessingError(f"품질 검수 API 연결에 실패했습니다: {exc}") from exc

    output_text = extract_response_text(raw_payload)
    if not output_text:
        raise AIProcessingError("품질 검수 결과를 받지 못했습니다.")

    try:
        reviewed = json.loads(strip_code_fence(output_text))
    except json.JSONDecodeError as exc:
        raise AIProcessingError("품질 검수 결과가 JSON 형식이 아닙니다.") from exc

    if not isinstance(reviewed, dict):
        raise AIProcessingError("품질 검수 결과가 올바른 객체 형식이 아닙니다.")

    merged = {**draft_record, **reviewed}
    if isinstance(draft_record.get("student_summary"), dict) or isinstance(reviewed.get("student_summary"), dict):
        merged["student_summary"] = {
            **(draft_record.get("student_summary") or {}),
            **(reviewed.get("student_summary") or {}),
        }
    return merged


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
    article_url: str = "",
    article_text: str = "",
) -> dict[str, Any]:
    speaker_turns = parse_speaker_turns(transcript_text)
    student_turns = [turn["text"] for turn in speaker_turns if turn["speaker"] == "student"]
    teacher_turns = [turn["text"] for turn in speaker_turns if turn["speaker"] == "teacher"]
    transcript_sentences = split_sentences(transcript_text)
    article_sentences = split_sentences(article_text)
    source_text = combine_source_texts(article_text, transcript_text)
    source_sentences = article_sentences or transcript_sentences

    recommended_title = article_title.strip() or infer_title_from_text(article_text or transcript_text)
    topic = (
        f"저는 {recommended_title} 기사에서 중요하게 느껴진 내용을 중심으로 정리해봤어요."
        if recommended_title
        else "저는 오늘 읽은 기사에서 중요하게 느껴진 내용을 중심으로 정리해봤어요."
    )

    context_sentence = first_non_empty(
        join_sentences(article_sentences[:2]),
        join_sentences(student_turns[:2]),
        join_sentences(transcript_sentences[:2]),
        join_sentences(teacher_turns[:2]),
        "기사 내용을 읽으면서 왜 중요한지와 제 생각을 같이 정리해봤어요.",
    )

    understanding = first_non_empty(
        pick_learning_sentence(source_sentences),
        pick_learning_sentence(transcript_sentences),
        join_sentences(student_turns[:2]),
        context_sentence,
        "기사 내용을 제 말로 다시 정리해보면서 제가 이해한 점을 남겼어요.",
    )

    student_thought = first_non_empty(
        pick_opinion_sentence(student_turns),
        join_sentences(student_turns[:2]),
        "기사에서 중요하다고 느낀 점을 제 경험이랑 연결해서 생각해봤어요.",
    )

    difficult_part = first_non_empty(
        pick_difficult_sentence(student_turns + transcript_sentences + article_sentences),
        "숫자나 근거가 나오는 부분을 바로 이해하는 건 조금 헷갈렸어요.",
    )
    thinking_point = build_thinking_point(recommended_title, source_text, student_thought)
    one_line_feeling = build_one_line_feeling(recommended_title, source_text, tone_samples)
    summary_text = build_student_summary_text(
        article_title=recommended_title,
        topic=topic,
        understanding=understanding,
        student_thought=student_thought,
        difficult_part=difficult_part,
        thinking_point=thinking_point,
    )
    dialogue_summary = first_non_empty(
        build_student_dialogue_summary(
            article_title=recommended_title,
            topic=topic,
            understanding=understanding,
            one_line_feeling=one_line_feeling,
        ),
        one_line_feeling,
        "오늘 읽은 기사에서 기억에 남은 생각을 짧게 남겼어요.",
    )
    lesson_headline = build_lesson_headline(
        article_title=recommended_title,
        dialogue_summary=dialogue_summary,
        student_summary={
            "student_thought": student_thought,
            "one_line_feeling": one_line_feeling,
        },
    )
    summary_points = build_fallback_summary_points(
        transcript_text=source_text,
        article_title=recommended_title,
        summary_text=summary_text,
        student_summary={
            "topic": topic,
            "understanding": understanding,
            "student_thought": student_thought,
            "difficult_part": difficult_part,
            "thinking_point": thinking_point,
            "one_line_feeling": one_line_feeling,
        },
    )

    return {
        "recommended_title": recommended_title,
        "lesson_headline": lesson_headline,
        "summary_text": summary_text,
        "dialogue_summary": dialogue_summary,
        "summary_points": summary_points,
        "speaker_turns": speaker_turns,
        "concept_cards": build_fallback_concept_cards(
            transcript_text=source_text,
            article_title=recommended_title,
            summary_text=summary_text,
            difficult_part=difficult_part,
        ),
        "student_summary": {
            "topic": topic,
            "understanding": understanding,
            "student_thought": student_thought,
            "difficult_part": difficult_part,
            "thinking_point": thinking_point,
            "one_line_feeling": one_line_feeling,
        },
    }


def normalize_student_voice_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)

    for key in ["lesson_headline", "summary_text", "dialogue_summary"]:
        normalized[key] = apply_light_polite_tone(normalize_student_voice_text(normalized.get(key, "")))

    summary_points: list[dict[str, str]] = []
    raw_points = normalized.get("summary_points") if isinstance(normalized.get("summary_points"), list) else []
    for raw_point in raw_points:
        if not isinstance(raw_point, dict):
            continue
        title = str(raw_point.get("title", "")).strip()
        detail = apply_light_polite_tone(normalize_student_voice_text(str(raw_point.get("detail", "")).strip()))
        if detail:
            summary_points.append({"title": title, "detail": detail})
    if summary_points:
        normalized["summary_points"] = normalize_summary_points(summary_points)

    concept_cards: list[dict[str, Any]] = []
    raw_cards = normalized.get("concept_cards") if isinstance(normalized.get("concept_cards"), list) else []
    for raw_card in raw_cards:
        if not isinstance(raw_card, dict):
            continue
        card = dict(raw_card)
        card["lesson_connection"] = apply_light_polite_tone(
            normalize_student_voice_text(card.get("lesson_connection", ""))
        )
        concept_cards.append(card)
    if concept_cards:
        normalized["concept_cards"] = normalize_concept_cards(concept_cards)

    raw_student_summary = normalized.get("student_summary", {})
    student_summary = dict(raw_student_summary) if isinstance(raw_student_summary, dict) else {}
    for key in ["topic", "understanding", "student_thought", "difficult_part", "thinking_point", "one_line_feeling"]:
        student_summary[key] = apply_light_polite_tone(normalize_student_voice_text(student_summary.get(key, "")))
    normalized["student_summary"] = student_summary
    return normalized


def build_notion_exports(
    *,
    lesson_date: str,
    article_title: str,
    lesson_headline: str,
    summary_text: str,
    dialogue_summary: str,
    summary_points: list[dict[str, str]],
    student_summary: dict[str, str],
    concept_cards: list[dict[str, Any]],
    transcript_text: str,
) -> dict[str, str]:
    title = article_title.strip() or "오늘 읽음 기록"
    headline = lesson_headline.strip() or dialogue_summary.strip() or "오늘 읽은 기사와 내 생각을 정리했다."
    summary_body = summary_text.strip() or dialogue_summary.strip() or "기록 없음"

    concept_lines: list[str] = []
    for card in concept_cards:
        term = str(card.get("term", "")).strip()
        meaning = str(card.get("meaning", "")).strip()
        related_terms = [str(item).strip() for item in card.get("related_terms", []) if str(item).strip()]
        connection = str(card.get("lesson_connection", "")).strip()
        if not term:
            continue
        concept_lines.extend(
            [
                f"### {term}",
                meaning or "기록 없음",
                f"- 관련 용어: {', '.join(related_terms) if related_terms else '기록 없음'}",
                f"- 기록 연결: {connection or '기록 없음'}",
                "",
            ]
        )
    concepts_markdown = "\n".join(concept_lines).strip() or "기록 없음"
    summary_point_lines = [
        f"- {point.get('title', '').strip() or '핵심 포인트'}: {point.get('detail', '').strip() or '기록 없음'}"
        for point in summary_points
        if str(point.get("detail", "")).strip()
    ]
    summary_points_markdown = "\n".join(summary_point_lines).strip() or "- 기록 없음"

    student_markdown = "\n".join(
        [
            f"# 내 메모 | {title}",
            "",
            f"- 기록 날짜: {lesson_date or '미입력'}",
            f"- 한 줄 메모: {student_summary.get('one_line_feeling', '').strip() or '기록 없음'}",
            "",
            "## 기사 주제",
            student_summary.get("topic", "").strip() or "기록 없음",
            "",
            "## 제가 이해한 핵심",
            student_summary.get("understanding", "").strip() or "기록 없음",
            "",
            "## 기억에 남은 생각",
            student_summary.get("student_thought", "").strip() or "기록 없음",
            "",
            "## 조금 더 보고 싶은 부분",
            student_summary.get("difficult_part", "").strip() or "기록 없음",
            "",
            "## 더 생각해볼 점",
            student_summary.get("thinking_point", "").strip() or "기록 없음",
            "",
            "## 한 줄 메모",
            student_summary.get("one_line_feeling", "").strip() or "기록 없음",
        ]
    ).strip()

    summary_markdown = "\n".join(
        [
            f"# 내가 정리한 기사 내용 | {title}",
            "",
            f"- 기록 날짜: {lesson_date or '미입력'}",
            "",
            summary_body,
            "",
            "## 핵심 포인트",
            summary_points_markdown,
        ]
    ).strip()

    combined_markdown = "\n".join(
        [
            f"# {title}",
            "",
            f"> {headline}",
            "",
            f"- 기록 날짜: {lesson_date or '미입력'}",
            "",
            "## 내가 정리한 기사 내용",
            summary_body,
            "",
            "## 핵심 포인트",
            summary_points_markdown,
            "",
            "## 새롭게 알게 된 개념",
            concepts_markdown,
            "",
            "## 내 메모",
            f"### 기사 주제\n{student_summary.get('topic', '').strip() or '기록 없음'}",
            "",
            f"### 제가 이해한 핵심\n{student_summary.get('understanding', '').strip() or '기록 없음'}",
            "",
            f"### 기억에 남은 생각\n{student_summary.get('student_thought', '').strip() or '기록 없음'}",
            "",
            f"### 조금 더 보고 싶은 부분\n{student_summary.get('difficult_part', '').strip() or '기록 없음'}",
            "",
            f"### 더 생각해볼 점\n{student_summary.get('thinking_point', '').strip() or '기록 없음'}",
            "",
            f"### 한 줄 메모\n{student_summary.get('one_line_feeling', '').strip() or '기록 없음'}",
        ]
    ).strip()

    return {
        "summary_markdown": summary_markdown,
        "summary_points_markdown": summary_points_markdown,
        "concepts_markdown": concepts_markdown,
        "student_markdown": student_markdown,
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

    monologue: list[dict[str, str]] = []
    for index, sentence in enumerate(sentences[:8]):
        monologue.append({"speaker": "student", "text": sentence})
    return monologue


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
        return "오늘 읽은 기사"

    cleaned = re.sub(r"^(학생|선생님|teacher|student)\s*[:：-]\s*", "", sentences[0], flags=re.IGNORECASE)
    cleaned = re.sub(r"\[[^\]]+\]", "", cleaned).strip()
    if 6 <= len(cleaned) <= 28:
        return cleaned
    if cleaned:
        return f"{cleaned[:18].strip()} 관련 기사"
    return "오늘 읽은 기사"


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
        return f"{article_title} 기사를 읽고 내가 중요하게 느낀 점을 다시 적어봤다."
    return "오늘 읽은 기사에서 내가 중요하게 느낀 점을 다시 적어봤다."


def normalize_student_voice_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""

    replacements = (
        ("오늘 수업에서는", "오늘 기사에서는"),
        ("오늘 수업에서", "오늘 기사 내용을 읽으면서"),
        ("이번 수업에서는", "이번 기록에서는"),
        ("이번 수업에서", "이번 기록을 정리하면서"),
        ("기사 내용을 읽고", "기사 내용을 읽으면서"),
        ("학생은", "나는"),
        ("학생이", "내가"),
        ("학생을", "나를"),
        ("학생에게", "나에게"),
        ("학생의", "내"),
        ("학생 입장에서는", "내 입장에서는"),
        ("학생 입장에서", "내 입장에서"),
        ("함께 배웠다", "읽으면서 알게 됐다"),
        ("함께 살펴봤다", "읽으면서 다시 보게 됐다"),
        ("함께 정리했다", "내가 다시 정리해봤다"),
        ("오늘 기록에서 함께 다룬", "오늘 기사에서 내가 같이 기억해두고 싶은"),
    )
    for before, after in replacements:
        normalized = normalized.replace(before, after)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def apply_light_polite_tone(text: str) -> str:
    polished = str(text or "").strip()
    if not polished:
        return ""

    replacements = (
        ("나는 ", "저는 "),
        ("내가 ", "제가 "),
        ("내 입장에서는", "제 입장에서는"),
        ("내 생각", "제 생각"),
        ("내 경험", "제 경험"),
        ("내 생활", "제 생활"),
        ("내 말로", "제 말로"),
        ("정리해봤다.", "정리해봤어요."),
        ("정리했다.", "정리했어요."),
        ("적어봤다.", "적어봤어요."),
        ("생각해봤다.", "생각해봤어요."),
        ("떠올려봤다.", "떠올려봤어요."),
        ("남겼다.", "남겼어요."),
        ("느꼈다.", "느꼈어요."),
        ("기억에 남았다.", "기억에 남았어요."),
        ("알게 됐다.", "알게 됐어요."),
        ("알게 됐다.", "알게 됐어요."),
        ("이해하게 됐다.", "이해하게 됐어요."),
        ("이해했다.", "이해했어요."),
        ("이어졌다.", "이어졌어요."),
        ("보였다.", "보였어요."),
        ("중요했다.", "중요했어요."),
        ("궁금했다.", "궁금했어요."),
        ("헷갈렸다.", "헷갈렸어요."),
        ("도움이 됐다.", "도움이 됐어요."),
        ("필요했다.", "필요했어요."),
        ("였다.", "였어요."),
        ("이었다.", "이었어요."),
        ("좋겠다.", "좋겠어요."),
        ("싶다.", "싶어요."),
        ("생각해.", "생각해요."),
        ("다가왔어.", "다가왔어요."),
        ("재미있었어.", "재미있었어요."),
        ("느껴졌어.", "느껴졌어요."),
        ("알게 됐어.", "알게 됐어요."),
        ("남았어.", "남았어요."),
        ("보였어.", "보였어요."),
        ("컸다.", "컸어요."),
    )
    for before, after in replacements:
        polished = polished.replace(before, after)
    return polished


def build_student_summary_text(
    *,
    article_title: str,
    topic: str,
    understanding: str,
    student_thought: str,
    difficult_part: str,
    thinking_point: str,
) -> str:
    final_reflection = first_non_empty(thinking_point, difficult_part)
    if student_thought and student_thought in final_reflection:
        final_reflection = difficult_part

    candidates = [
        topic,
        understanding,
        student_thought,
        final_reflection,
    ]
    unique_sentences: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        sentence = apply_light_polite_tone(normalize_student_voice_text(candidate))
        if not sentence:
            continue
        dedupe_key = re.sub(r"\s+", " ", sentence)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique_sentences.append(sentence)

    if unique_sentences:
        return join_sentences(unique_sentences[:4])
    if article_title:
        return f"저는 {article_title} 기사를 읽고 이해한 내용과 떠오른 생각을 다시 정리해봤어요."
    return "저는 오늘 읽은 기사에서 이해한 내용과 떠오른 생각을 다시 정리해봤어요."


def build_student_dialogue_summary(
    *,
    article_title: str,
    topic: str,
    understanding: str,
    one_line_feeling: str,
) -> str:
    candidate = first_non_empty(one_line_feeling, understanding, topic)
    cleaned = apply_light_polite_tone(normalize_student_voice_text(candidate))
    if cleaned:
        sentences = split_sentences(cleaned)
        return sentences[0] if sentences else cleaned
    if article_title:
        return f"저는 {article_title} 기사에서 기억에 남은 점을 짧게 정리해봤어요."
    return "저는 오늘 읽은 기사에서 기억에 남은 점을 짧게 정리해봤어요."


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
        return f"기사 내용을 다시 정리하면서 {sentences[0][:60].rstrip()} 부분이 특히 기억에 남았다."
    return ""


def pick_difficult_sentence(sentences: list[str]) -> str:
    keywords = ["어려", "헷갈", "잘 모르", "모르겠", "복잡", "통계", "숫자"]
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence
    return ""


def build_one_line_feeling(article_title: str, transcript_text: str, tone_samples: list[str]) -> str:
    if "공감" in transcript_text:
        return "제 경험이랑 비슷한 부분이 있어서 생각보다 공감되는 기사였어요."
    if "어렵" in transcript_text or "헷갈" in transcript_text:
        return "완전히 쉽지는 않았지만 생각할 게 많았던 기사였어요."
    if article_title:
        return f"{article_title} 이야기가 생각보다 제 생활이랑 가까워서 기억에 남았어요."
    if tone_samples:
        return "제가 직접 말한 생각이 정리되니까 내용이 더 또렷하게 남는 느낌이었어요."
    return "짧게 말해봤는데도 다시 생각해볼 점이 남는 기사였어요."


def normalize_concept_cards(raw_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_cards, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_card in raw_cards:
        if not isinstance(raw_card, dict):
            continue
        term = str(raw_card.get("term", "")).strip()
        meaning = str(raw_card.get("meaning", "")).strip()
        related_terms = [str(item).strip() for item in raw_card.get("related_terms", []) if str(item).strip()]
        lesson_connection = str(raw_card.get("lesson_connection", "")).strip()
        if not term:
            continue
        normalized.append(
            {
                "term": term,
                "meaning": meaning or "기록 없음",
                "related_terms": related_terms[:4],
                "lesson_connection": lesson_connection or "기록 없음",
            }
        )
    return normalized


def normalize_summary_points(raw_points: list[Any]) -> list[dict[str, str]]:
    if not isinstance(raw_points, list):
        return []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()

    for index, raw_point in enumerate(raw_points, start=1):
        if isinstance(raw_point, dict):
            title = str(raw_point.get("title", "")).strip()
            detail = str(raw_point.get("detail", "")).strip()
        else:
            title = f"핵심 포인트 {index}"
            detail = str(raw_point).strip()

        if not detail:
            continue

        dedupe_key = re.sub(r"\s+", " ", detail).lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        normalized.append(
            {
                "title": title or f"핵심 포인트 {len(normalized) + 1}",
                "detail": detail,
            }
        )

    return normalized[:4]


def build_fallback_summary_points(
    *,
    transcript_text: str,
    article_title: str,
    summary_text: str,
    student_summary: dict[str, str],
) -> list[dict[str, str]]:
    summary_sentences = split_sentences(summary_text)
    candidates = [
        (
            "기사 주제",
            first_non_empty(
                student_summary.get("topic", ""),
                summary_sentences[0] if summary_sentences else "",
                f"{article_title}를 중심으로 내용을 정리했다." if article_title else "",
            ),
        ),
        (
            "내가 이해한 핵심",
            first_non_empty(
                student_summary.get("understanding", ""),
                summary_sentences[1] if len(summary_sentences) > 1 else "",
                summary_text,
            ),
        ),
        (
            "내가 중요하게 본 생각",
            first_non_empty(
                student_summary.get("student_thought", ""),
                pick_opinion_sentence(split_sentences(transcript_text)),
            ),
        ),
        (
            "다시 생각해볼 질문",
            first_non_empty(
                student_summary.get("thinking_point", ""),
                student_summary.get("difficult_part", ""),
            ),
        ),
    ]

    return normalize_summary_points(
        [
            {"title": title, "detail": detail}
            for title, detail in candidates
            if detail.strip()
        ]
        or [{"title": "오늘 기록 핵심", "detail": summary_text or "기록 없음"}]
    )


def build_fallback_concept_cards(
    *,
    transcript_text: str,
    article_title: str,
    summary_text: str,
    difficult_part: str,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    lowered = transcript_text.lower()

    concept_library = [
        {
            "aliases": ["스태그플레이션"],
            "term": "스태그플레이션",
            "meaning": "경기는 침체되는데 물가는 계속 오르는 상태를 뜻한다.",
            "related_terms": ["인플레이션", "경기 침체", "실업", "물가 상승"],
        },
        {
            "aliases": ["환율"],
            "term": "환율",
            "meaning": "한 나라 돈을 다른 나라 돈과 바꿀 때의 비율이다.",
            "related_terms": ["고환율", "수입 물가", "달러", "원화"],
        },
        {
            "aliases": ["인플레이션", "물가", "물가 상승"],
            "term": "인플레이션",
            "meaning": "전반적인 물가가 계속 오르는 현상을 뜻한다.",
            "related_terms": ["물가 상승", "구매력", "금리", "통화량"],
        },
        {
            "aliases": ["오일 쇼크", "석유"],
            "term": "오일 쇼크",
            "meaning": "국제 유가가 급등해 경제 전반에 충격을 주는 상황이다.",
            "related_terms": ["국제 유가", "에너지 가격", "중동", "물가"],
        },
        {
            "aliases": ["나비효과"],
            "term": "나비효과",
            "meaning": "아주 작은 변화가 나중에 큰 결과로 이어질 수 있다는 생각이다.",
            "related_terms": ["연쇄 반응", "변수", "영향", "선택"],
        },
        {
            "aliases": ["담수화"],
            "term": "담수화 시설",
            "meaning": "바닷물에서 소금기를 빼 생활용 물을 만드는 시설이다.",
            "related_terms": ["물 부족", "인프라", "중동", "생활 자원"],
        },
    ]

    for item in concept_library:
        if any(alias.lower() in lowered for alias in item["aliases"]):
            cards.append(
                {
                    "term": item["term"],
                    "meaning": item["meaning"],
                    "related_terms": item["related_terms"],
                    "lesson_connection": difficult_part
                    or summary_text
                    or "이 개념은 오늘 기사 내용을 이해할 때 내가 같이 기억해두고 싶은 부분이다.",
                }
            )

    if article_title and ("역사" in article_title or "선택" in transcript_text):
        cards.append(
            {
                "term": "선택과 역사",
                "meaning": "개인의 선택과 사건이 쌓여 사회와 역사의 흐름을 만든다는 관점이다.",
                "related_terms": ["누적", "결정", "현재", "미래"],
                "lesson_connection": summary_text or "이 개념이 있어야 오늘 읽은 기사와 지금 현실이 어떻게 이어지는지 더 잘 보였다.",
            }
        )

    if not cards:
        cards.append(
            {
                "term": article_title.strip() or "핵심 개념",
                "meaning": summary_text or "오늘 기사에서 중심이 된 개념을 간단히 정리했다.",
                "related_terms": ["원인", "영향", "사례"],
                "lesson_connection": difficult_part or "기사 전체 흐름을 이해할 때 내가 다시 떠올려보고 싶은 개념이다.",
            }
        )

    return normalize_concept_cards(cards[:5])


def build_thinking_point(article_title: str, transcript_text: str, student_thought: str) -> str:
    if student_thought:
        return "제가 왜 그렇게 느꼈는지 한 번 더 떠올려보고 싶어요."
    if "이유" in transcript_text or "왜" in transcript_text:
        return "오늘 나온 이야기 중 가장 공감된 부분이 왜 기억에 남았는지 스스로 더 풀어보고 싶다."
    if article_title:
        return f"{article_title}와 비슷한 상황이 내 주변에도 있는지 더 떠올려보고 싶다."
    return "오늘 기록에서 가장 기억에 남은 한 장면을 다시 떠올려보고 싶다."
