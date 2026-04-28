from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .academy import load_academy_data
from .config import PDF_OUTPUT_DIR, ROOT_DIR, TMP_PDF_DIR


FONT_REGULAR = "AcademyPdfRegular"
FONT_BOLD = "AcademyPdfBold"
def generate_academy_report_pdf(student_id: str) -> dict[str, Any]:
    payload = load_academy_data()
    student = next((item for item in payload.get("students", []) if item.get("id") == student_id), None)
    if student is None:
        raise KeyError(student_id)

    lesson_class = next(
        (item for item in payload.get("classes", []) if item.get("id") == student.get("class_id")),
        {},
    )

    register_pdf_fonts()

    filename = build_pdf_filename(
        student_id=student_id,
        student_name=str(student.get("name", "")),
    )
    pdf_bytes = build_pdf_bytes(
        academy=payload.get("academy", {}),
        student=student,
        lesson_class=lesson_class,
    )
    file_path = persist_pdf_copy(filename=filename, content=pdf_bytes)

    return {
        "filename": filename,
        "file_path": file_path,
        "content": pdf_bytes,
    }


def build_pdf_bytes(*, academy: dict[str, Any], student: dict[str, Any], lesson_class: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=f"{student.get('name', '학생')} 학부모 결과지",
        author=str(academy.get("teacher_name", "")),
    )

    styles = build_styles()
    report = dict(student.get("report", {}) or {})
    test = dict(student.get("test", {}) or {})
    profile = dict(student.get("profile", {}) or {})

    story: list[Any] = []
    story.extend(
        [
            build_header_block(academy=academy, student=student, lesson_class=lesson_class, styles=styles),
            Spacer(1, 8 * mm),
            build_meta_table(academy=academy, student=student, lesson_class=lesson_class, test=test, styles=styles, doc_width=doc.width),
            Spacer(1, 6 * mm),
            build_summary_block(report=report, styles=styles),
            Spacer(1, 5 * mm),
            build_section_grid(
                sections=[
                    ("수업 태도", report.get("attitude", "")),
                    ("성취 내용", report.get("achievement", "")),
                    ("숙제 수행", report.get("homework", "")),
                    ("어려웠던 부분", report.get("difficulty", "")),
                    ("테스트 분석", report.get("test", "")),
                    ("다음 수업 계획", report.get("next_step", "")),
                ],
                styles=styles,
                doc_width=doc.width,
            ),
            Spacer(1, 5 * mm),
            build_message_block(report=report, styles=styles),
            Spacer(1, 4 * mm),
            build_profile_note(profile=profile, styles=styles),
        ]
    )

    doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)
    return buffer.getvalue()


def register_pdf_fonts() -> None:
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames() and FONT_BOLD in pdfmetrics.getRegisteredFontNames():
        return

    for regular_path, bold_path in build_font_candidates():
        if not regular_path.exists() or not bold_path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
            return
        except Exception:
            continue

    raise FileNotFoundError(
        "Korean PDF font not found. Set ACADEMY_PDF_FONT_REGULAR and ACADEMY_PDF_FONT_BOLD or add a supported font."
    )


def build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "AcademyEyebrow",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#c79d54"),
            alignment=TA_LEFT,
        ),
        "brand": ParagraphStyle(
            "AcademyBrand",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#f6efe5"),
        ),
        "title": ParagraphStyle(
            "AcademyTitle",
            parent=sample["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=28,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "AcademySubtitle",
            parent=sample["Normal"],
            fontName=FONT_REGULAR,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#e8e0d4"),
        ),
        "meta_label": ParagraphStyle(
            "AcademyMetaLabel",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#8f806c"),
        ),
        "meta_value": ParagraphStyle(
            "AcademyMetaValue",
            parent=sample["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#2a2420"),
        ),
        "summary": ParagraphStyle(
            "AcademySummary",
            parent=sample["BodyText"],
            fontName=FONT_BOLD,
            fontSize=12.5,
            leading=19,
            textColor=colors.HexColor("#2b241f"),
        ),
        "card_title": ParagraphStyle(
            "AcademyCardTitle",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#8f6a2d"),
        ),
        "card_body": ParagraphStyle(
            "AcademyCardBody",
            parent=sample["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=10.2,
            leading=16,
            textColor=colors.HexColor("#302823"),
        ),
        "message_title": ParagraphStyle(
            "AcademyMessageTitle",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1d3557"),
        ),
        "message_body": ParagraphStyle(
            "AcademyMessageBody",
            parent=sample["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor("#2b241f"),
        ),
        "footer": ParagraphStyle(
            "AcademyFooter",
            parent=sample["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#8f806c"),
            alignment=TA_CENTER,
        ),
    }


def build_header_block(
    *,
    academy: dict[str, Any],
    student: dict[str, Any],
    lesson_class: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> Table:
    title = f"{escape(str(student.get('name', '학생')))} 학부모 결과지"
    subtitle = "수업 메모와 단원 테스트 분석을 바탕으로 현재 학습 흐름을 정리한 리포트입니다."
    academy_name = escape(str(academy.get("name", "Academy")))
    unit_name = escape(str(lesson_class.get("unit_name", "단원 정보 준비 중")))

    table = Table(
        [
            [Paragraph(academy_name, styles["brand"])],
            [Paragraph(title, styles["title"])],
            [Paragraph(subtitle, styles["subtitle"])],
            [Paragraph(f"현재 단원: {unit_name}", styles["subtitle"])],
        ],
        colWidths=[174 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1f344d")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#304d73")),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 15),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )
    return table


def build_meta_table(
    *,
    academy: dict[str, Any],
    student: dict[str, Any],
    lesson_class: dict[str, Any],
    test: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    doc_width: float,
) -> Table:
    rows = [
        [
            build_meta_cell("학생", student.get("name", "-"), styles),
            build_meta_cell("반", lesson_class.get("name", "-"), styles),
            build_meta_cell("담당", academy.get("teacher_name", "-"), styles),
        ],
        [
            build_meta_cell("출력일", datetime.now().strftime("%Y.%m.%d"), styles),
            build_meta_cell("단원", lesson_class.get("unit_name", "-"), styles),
            build_meta_cell("테스트", test.get("score_label", "점수 미입력"), styles),
        ],
    ]
    table = Table(rows, colWidths=[doc_width / 3.0] * 3, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fbf7f1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e5d7c3")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#efe4d5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def build_meta_cell(label: str, value: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Paragraph(escape(label), styles["meta_label"]),
        Spacer(1, 1.5 * mm),
        Paragraph(escape(normalize_pdf_text(value, "-")), styles["meta_value"]),
    ]


def build_summary_block(*, report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    summary = normalize_pdf_text(
        report.get("summary"),
        "이번 수업 흐름을 기준으로 학습 상태와 다음 보완 방향을 정리했습니다.",
    )
    table = Table([[Paragraph(escape(summary), styles["summary"])]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7efe2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e3cfae")),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return table


def build_section_grid(
    *,
    sections: list[tuple[str, Any]],
    styles: dict[str, ParagraphStyle],
    doc_width: float,
) -> Table:
    card_width = (doc_width - 8) / 2.0
    rows: list[list[Any]] = []
    current: list[Any] = []

    for title, body in sections:
        current.append(build_section_card(title=title, body=body, styles=styles, width=card_width))
        if len(current) == 2:
            rows.append(current)
            current = []

    if current:
        current.append(Spacer(1, 1))
        rows.append(current)

    table = Table(rows, colWidths=[card_width, card_width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_section_card(*, title: str, body: Any, styles: dict[str, ParagraphStyle], width: float) -> Table:
    content = [
        [Paragraph(escape(title), styles["card_title"])],
        [Spacer(1, 2 * mm)],
        [Paragraph(escape(normalize_pdf_text(body, "기록이 아직 입력되지 않았습니다.")), styles["card_body"])],
    ]
    table = Table(content, colWidths=[width - 10])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#eadfd2")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def build_message_block(*, report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    message = normalize_pdf_text(
        report.get("message_draft"),
        "학부모 전달 메시지가 아직 생성되지 않았습니다.",
    )
    table = Table(
        [
            [Paragraph("학부모 전달 메시지", styles["message_title"])],
            [Spacer(1, 2 * mm)],
            [Paragraph(escape(message), styles["message_body"])],
        ],
        colWidths=[174 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4f8")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#c6d7e6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return table


def build_profile_note(*, profile: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Paragraph:
    state = normalize_pdf_text(profile.get("state"), "학습 흐름 점검 중")
    summary = normalize_pdf_text(profile.get("summary"), "학생별 프로필 요약은 다음 수업 이후 더 구체화됩니다.")
    note = f"현재 흐름: {state} | 참고 메모: {summary}"
    return Paragraph(escape(note), styles["footer"])


def draw_page_frame(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#eadfd2"))
    canvas.rect(12 * mm, 12 * mm, A4[0] - 24 * mm, A4[1] - 24 * mm, stroke=1, fill=0)
    canvas.setFont(FONT_REGULAR, 8.5)
    canvas.setFillColor(colors.HexColor("#8f806c"))
    canvas.drawString(doc.leftMargin, 10 * mm, "Prime Academy Parent Report")
    canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_font_candidates() -> list[tuple[Path, Path]]:
    env_regular = os.getenv("ACADEMY_PDF_FONT_REGULAR", "").strip()
    env_bold = os.getenv("ACADEMY_PDF_FONT_BOLD", "").strip()
    candidates: list[tuple[Path, Path]] = []

    if env_regular and env_bold:
        candidates.append((Path(env_regular).expanduser(), Path(env_bold).expanduser()))

    candidates.extend(
        [
            (ROOT_DIR / "static" / "fonts" / "NanumGothic.ttf", ROOT_DIR / "static" / "fonts" / "NanumGothicBold.ttf"),
            (Path(r"C:\Windows\Fonts\malgun.ttf"), Path(r"C:\Windows\Fonts\malgunbd.ttf")),
            (Path(r"C:\Windows\Fonts\NanumGothic.ttf"), Path(r"C:\Windows\Fonts\NanumGothicBold.ttf")),
            (Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"), Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")),
            (Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"), Path("/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf")),
            (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")),
        ]
    )
    return candidates


def persist_pdf_copy(*, filename: str, content: bytes) -> Path | None:
    for base_dir in (PDF_OUTPUT_DIR, TMP_PDF_DIR):
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
            file_path = base_dir / filename
            file_path.write_bytes(content)
            return file_path
        except OSError:
            continue
    return None


def build_pdf_filename(*, student_id: str, student_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_name = build_safe_filename_part(student_id or student_name)
    return f"academy-report-{safe_name}-{timestamp}-{uuid4().hex[:6]}.pdf"


def build_safe_filename_part(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "student"


def normalize_pdf_text(value: Any, fallback: str) -> str:
    normalized = " ".join(str(value or "").split()).strip()
    return normalized or fallback
