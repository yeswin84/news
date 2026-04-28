from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .config import ACADEMY_DB_PATH, DATA_DIR

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows
    fcntl = None

try:
    import msvcrt  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None


ACADEMY_LOCK_PATH = ACADEMY_DB_PATH.with_suffix(".lock")
ACADEMY_THREAD_LOCK = threading.RLock()


DEFAULT_ACADEMY_DATA: dict[str, Any] = {
    "academy": {
        "name": "Prime Academy",
        "product_label": "Math Studio OS",
        "teacher_name": "김소연 선생님",
        "date_label": "2026년 4월 4일 토요일",
        "hero_focus": {
            "title": "선생님은 편하게 적고, 시스템은 문서로 정리합니다.",
            "description": (
                "학생별 자연어 메모를 남기면 수업일지, 테스트 분석, 학부모용 전달 메시지, "
                "PDF 결과지까지 연결되는 구조를 실제 운영 기준으로 다듬는 중입니다."
            ),
        },
    },
    "classes": [
        {
            "id": "class-middle2-a",
            "name": "중2 A반",
            "grade": "중2",
            "teacher_name": "김소연 선생님",
            "schedule_time": "16:00",
            "schedule_label": "토요일 16:00",
            "unit_name": "일차함수 그래프 해석",
            "status": "live",
            "student_ids": ["yoonseo", "minjun", "seoha", "jihoo"],
        },
        {
            "id": "class-middle3-advanced",
            "name": "중3 심화반",
            "grade": "중3",
            "teacher_name": "김소연 선생님",
            "schedule_time": "18:00",
            "schedule_label": "토요일 18:00",
            "unit_name": "이차방정식 실전 유형",
            "status": "test_queue",
            "student_ids": [],
        },
        {
            "id": "class-high1-internal",
            "name": "고1 내신반",
            "grade": "고1",
            "teacher_name": "김소연 선생님",
            "schedule_time": "20:00",
            "schedule_label": "토요일 20:00",
            "unit_name": "함수 기본 유형",
            "status": "report_queue",
            "student_ids": [],
        },
    ],
    "selected_class_id": "class-middle2-a",
    "selected_student_id": "yoonseo",
    "auto_outputs": [
        {
            "title": "수업일지",
            "body": "반 단위 기록과 학생별 특이사항을 정리해서 선생님 업무일지로 저장합니다.",
        },
        {
            "title": "테스트 분석",
            "body": "점수, 약한 개념, 다음 보완 포인트를 학생별 분석 메모로 자동 정리합니다.",
        },
        {
            "title": "학부모 결과지",
            "body": "전달 메시지와 문서형 PDF 초안까지 한 번에 이어집니다.",
        },
    ],
    "dashboard_notes": [
        "중2 A반 학생별 메모를 먼저 마무리하면 오늘 PDF 대기 건수가 바로 줄어듭니다.",
        "서하 학생은 테스트 상승 폭이 커서 학부모 메시지에 성장 코멘트를 적극 반영하는 것이 좋습니다.",
        "민준 학생은 숙제 누락과 풀이 생략이 반복되어 다음 수업 계획을 결과지에 명확히 넣어야 합니다.",
    ],
    "students": [
        {
            "id": "yoonseo",
            "name": "윤서",
            "class_id": "class-middle2-a",
            "status": "done",
            "status_label": "기록 완료",
            "status_copy": "집중도 좋고 개념 흐름은 안정적입니다.",
            "lesson": {
                "natural_note": (
                    "오늘 일차함수 그래프 해석은 잘 따라왔는데 기울기 부호가 바뀌는 부분에서 조금 헷갈려했습니다. "
                    "숙제는 80% 해왔고 계산은 안정적이지만 문제 해석 속도가 느린 편입니다."
                ),
                "achievement": "개념 이해 안정적",
                "homework": "80% 완료",
                "homework_mini": "80%",
                "difficulty": "기울기 부호 판별",
                "next_step": "문제 해석 속도 보완",
                "parent_message": (
                    "오늘은 일차함수 그래프 해석 단원을 진행했습니다. 윤서는 개념 흐름은 잘 따라왔고 계산도 안정적이었지만, "
                    "기울기 부호를 해석하는 구간에서 조금 헷갈려하는 모습이 있었습니다. 다음 시간에는 문제 해석 속도와 "
                    "부호 판단을 함께 보완하겠습니다."
                ),
                "tags": ["숙제 완료", "집중도 좋음", "개념 이해 보통 이상"],
            },
            "test": {
                "score_value": 86,
                "score_label": "86점",
                "trend_label": "전회 대비 +12",
                "strength": "계산 안정감이 있고 기본 개념 흐름은 정확하게 이해하고 있습니다.",
                "weakness": "기울기 부호를 그래프 방향과 연결하는 과정에서 판단이 흔들렸습니다.",
                "plan": "짧은 유형 반복과 문장제 해석 훈련을 함께 배치하는 것이 좋습니다.",
                "weak_concepts": ["기울기 부호 판별", "문장제 해석"],
            },
            "report": {
                "summary": (
                    "이번 단원에서는 개념 이해가 안정적으로 자리 잡고 있으며, 그래프 해석 속도와 부호 판별 정확도를 "
                    "보완하면 더 빠르게 성장할 수 있는 상태입니다."
                ),
                "attitude": "집중도는 전반적으로 좋았고 설명을 끝까지 듣고 정리하려는 태도가 안정적이었습니다.",
                "achievement": "그래프와 식의 기본 연결은 잘 수행했고 계산 실수는 많지 않았습니다.",
                "homework": "숙제는 80% 정도 수행했으며 풀이 흔적도 비교적 성실하게 남겼습니다.",
                "difficulty": "기울기 부호가 바뀌는 경우를 그래프 방향과 연결해서 이해하는 부분이 아직 불안정합니다.",
                "test": "86점으로 이전 대비 상승했습니다. 기본 문항은 안정적이지만 문장제에서 시간이 길어졌습니다.",
                "next_step": "다음 시간에는 짧은 그래프 판별 문제와 문장제 해석 훈련을 함께 진행할 예정입니다.",
                "message_draft": (
                    "안녕하세요. 오늘 윤서는 일차함수 그래프 해석 단원을 진행했고, 개념 이해는 안정적이었습니다. "
                    "다만 기울기 부호를 해석하는 구간에서 조금 헷갈려하여 다음 시간에 해당 부분을 보완하겠습니다."
                ),
            },
            "profile": {
                "state": "안정적 상승",
                "summary": (
                    "계산 안정감이 좋고 설명을 들은 뒤 정리하는 태도가 차분합니다. 다만 문장제 해석 속도는 "
                    "조금 더 끌어올릴 필요가 있습니다."
                ),
                "tags": ["그래프 해석", "집중도 좋음", "계산 안정", "문장제 속도 보완"],
            },
            "timeline": [
                {
                    "date": "04.04",
                    "title": "일차함수 그래프 해석",
                    "body": "개념 연결은 좋았지만 기울기 부호 판별에서 망설임이 있었습니다.",
                },
                {
                    "date": "04.02",
                    "title": "함수 값 찾기",
                    "body": "기본 유형은 빠르게 풀었고 실수도 거의 없었습니다.",
                },
                {
                    "date": "03.29",
                    "title": "좌표평면 복습",
                    "body": "그래프 읽기 감각이 많이 안정되었습니다.",
                },
            ],
            "communication": [
                {"date": "04.04", "title": "수업 후 전달", "body": "기울기 부호 해석 보완 예정 안내"},
                {"date": "03.30", "title": "숙제 체크", "body": "숙제 이행률 안정적으로 유지 중"},
            ],
        },
        {
            "id": "minjun",
            "name": "민준",
            "class_id": "class-middle2-a",
            "status": "care",
            "status_label": "보완 필요",
            "status_copy": "숙제 누락과 풀이 생략이 반복되고 있습니다.",
            "lesson": {
                "natural_note": (
                    "오늘 개념 설명은 들었지만 그래프와 식을 연결하는 문제에서 여러 번 멈췄습니다. 숙제를 많이 못 해왔고 "
                    "중간 풀이를 생략하는 습관이 있어 오답이 늘었습니다."
                ),
                "achievement": "기본 개념 재점검 필요",
                "homework": "40% 완료",
                "homework_mini": "40%",
                "difficulty": "그래프와 식 연결",
                "next_step": "풀이 과정 쓰기 습관",
                "parent_message": (
                    "오늘 수업에서는 그래프와 식을 연결하는 문제에서 어려움이 있었습니다. 숙제 수행량이 적어 개념 확인이 "
                    "충분하지 않았고, 중간 풀이를 생략하는 습관이 보여 다음 시간에는 풀이 과정 작성까지 함께 점검하겠습니다."
                ),
                "tags": ["숙제 미완료", "풀이 생략", "보완 필요"],
            },
            "test": {
                "score_value": 73,
                "score_label": "73점",
                "trend_label": "전회 대비 -4",
                "strength": "문제를 끝까지 보려는 태도는 유지되고 있습니다.",
                "weakness": "그래프에서 식으로 넘어가는 변환 문제와 풀이 생략이 주요 감점 요인이었습니다.",
                "plan": "숙제량 조정과 풀이 습관 교정이 먼저 필요합니다.",
                "weak_concepts": ["그래프와 식 연결", "풀이 과정 구성"],
            },
            "report": {
                "summary": "개념 자체보다는 적용 과정에서 흔들리는 모습이 많아, 풀이 습관과 숙제 이행을 함께 잡아주는 것이 우선입니다.",
                "attitude": "설명을 들을 때는 따라오지만 스스로 푸는 단계에서 멈추는 경우가 잦았습니다.",
                "achievement": "기본 유형은 일부 수행했으나 응용 연결에서 불안정했습니다.",
                "homework": "숙제 수행량이 부족하여 수업 이해가 충분히 이어지지 못했습니다.",
                "difficulty": "그래프와 식의 연결, 풀이 과정 구성에서 어려움이 있었습니다.",
                "test": "73점으로 이전 대비 소폭 하락했습니다. 개념 부족보다는 적용 과정의 흔들림이 컸습니다.",
                "next_step": "다음 시간에는 풀이 과정 쓰기와 숙제 관리부터 우선 보완할 예정입니다.",
                "message_draft": (
                    "안녕하세요. 민준이는 오늘 그래프와 식을 연결하는 유형에서 어려움이 있었습니다. 숙제 수행량이 부족했고 "
                    "중간 풀이를 생략하는 습관이 보여, 다음 시간에는 풀이 과정과 숙제 관리까지 함께 점검하겠습니다."
                ),
            },
            "profile": {
                "state": "관리 필요",
                "summary": (
                    "기본 개념은 설명을 들으면 이해하지만 스스로 적용하는 단계에서 흔들림이 큽니다. 숙제 이행과 풀이 습관 "
                    "관리가 중요합니다."
                ),
                "tags": ["숙제 관리", "풀이 습관", "그래프 연결", "보완 필요"],
            },
            "timeline": [
                {
                    "date": "04.04",
                    "title": "일차함수 그래프 해석",
                    "body": "풀이 과정이 짧아 오답 원인 확인이 어려웠습니다.",
                },
                {
                    "date": "04.02",
                    "title": "함수 값 찾기",
                    "body": "기본 유형은 가능했으나 응용 연결에서 멈췄습니다.",
                },
                {
                    "date": "03.29",
                    "title": "좌표평면 복습",
                    "body": "개념 이해보다 문제 적용에서 시간이 길었습니다.",
                },
            ],
            "communication": [
                {"date": "04.04", "title": "보완 안내", "body": "숙제 이행과 풀이 과정 점검 필요 전달"},
                {"date": "03.27", "title": "과제 점검", "body": "숙제 누락 반복으로 확인 요청"},
            ],
        },
        {
            "id": "seoha",
            "name": "서하",
            "class_id": "class-middle2-a",
            "status": "done",
            "status_label": "성장 폭 큼",
            "status_copy": "테스트 점수 상승이 커서 긍정 피드백이 좋습니다.",
            "lesson": {
                "natural_note": (
                    "그래프에서 식을 만드는 부분을 이전보다 훨씬 빠르게 풀었습니다. 숙제도 성실하게 해왔고 스스로 질문도 했습니다. "
                    "계산은 안정적이고 응용 문항 시도도 좋아졌습니다."
                ),
                "achievement": "성취도 높음",
                "homework": "100% 완료",
                "homework_mini": "100%",
                "difficulty": "문장제 마지막 조건 정리",
                "next_step": "응용 문항 확장",
                "parent_message": (
                    "오늘 수업에서는 이전보다 풀이 속도와 정확도가 모두 좋아졌습니다. 숙제도 성실하게 해왔고 스스로 질문하는 "
                    "태도도 좋아, 다음 단계 응용 문항으로 자연스럽게 확장해볼 수 있는 흐름입니다."
                ),
                "tags": ["숙제 완료", "질문 적극적", "응용 가능"],
            },
            "test": {
                "score_value": 92,
                "score_label": "92점",
                "trend_label": "전회 대비 +10",
                "strength": "속도와 정확도가 함께 좋아졌고 응용 문항 시도도 적극적이었습니다.",
                "weakness": "문장제 마지막 조건 정리에서만 약간의 흔들림이 있었습니다.",
                "plan": "다음 단원에서는 상위권 유형으로 확장해도 좋습니다.",
                "weak_concepts": ["문장제 마지막 조건", "응용 문항 정리"],
            },
            "report": {
                "summary": "이번 단원에서 전반적인 학습 흐름이 한 단계 올라왔고, 자신감과 문제 해결 속도 모두 긍정적으로 보였습니다.",
                "attitude": "수업 참여도가 좋고 질문 타이밍도 적절했습니다.",
                "achievement": "그래프와 식 연결을 빠르고 정확하게 수행했습니다.",
                "homework": "숙제 수행과 오답 정리가 매우 성실했습니다.",
                "difficulty": "문장제 마지막 조건 정리에서만 약간의 보완이 필요합니다.",
                "test": "92점으로 이전보다 상승했고 응용 문항까지 안정적으로 처리했습니다.",
                "next_step": "다음 단원에서는 응용 문항 비중을 조금 더 높여 확장 학습을 진행할 예정입니다.",
                "message_draft": (
                    "안녕하세요. 서하는 오늘 수업에서 풀이 속도와 정확도가 모두 좋아진 모습이었습니다. 숙제와 오답 정리도 "
                    "성실해 다음 단원부터는 응용 유형 비중을 조금 더 높여보겠습니다."
                ),
            },
            "profile": {
                "state": "상승 흐름 뚜렷",
                "summary": "학습 자신감이 올라왔고 질문의 질도 좋아졌습니다. 단순 반복보다 확장 문제를 적절히 섞어주는 것이 효과적입니다.",
                "tags": ["상승세", "질문 적극적", "숙제 성실", "응용 확장"],
            },
            "timeline": [
                {
                    "date": "04.04",
                    "title": "일차함수 그래프 해석",
                    "body": "이전보다 풀이 속도와 정확도가 눈에 띄게 향상되었습니다.",
                },
                {
                    "date": "04.02",
                    "title": "함수 값 찾기",
                    "body": "스스로 질문하며 약한 부분을 바로 정리했습니다.",
                },
                {
                    "date": "03.29",
                    "title": "좌표평면 복습",
                    "body": "기본기 정리가 잘 되면서 응용 시도가 늘었습니다.",
                },
            ],
            "communication": [
                {"date": "04.04", "title": "성장 피드백", "body": "테스트 점수 상승과 수업 태도 긍정 피드백 전달"},
                {"date": "03.31", "title": "숙제 칭찬", "body": "오답 정리 성실도 안내"},
            ],
        },
        {
            "id": "jihoo",
            "name": "지후",
            "class_id": "class-middle2-a",
            "status": "pending",
            "status_label": "작성 중",
            "status_copy": "수업 메모는 좋았고 결과지 정리만 남았습니다.",
            "lesson": {
                "natural_note": (
                    "개념 이해는 전체적으로 괜찮았고 그래프 해석도 큰 무리는 없었습니다. 다만 조건이 길어지면 문제를 다시 읽는 "
                    "횟수가 많아집니다. 숙제는 거의 다 해왔고 계산 실수는 적었습니다."
                ),
                "achievement": "보통 이상",
                "homework": "90% 완료",
                "homework_mini": "90%",
                "difficulty": "긴 문장 조건 해석",
                "next_step": "조건 분해 연습",
                "parent_message": (
                    "오늘 수업에서는 개념 이해와 계산 모두 안정적인 편이었습니다. 다만 문장이 길어진 문제에서 다시 읽는 횟수가 많아져, "
                    "다음 시간에는 조건을 나누어 읽는 연습을 추가로 진행하겠습니다."
                ),
                "tags": ["숙제 완료", "조건 해석 보완"],
            },
            "test": {
                "score_value": 88,
                "score_label": "88점",
                "trend_label": "전회 대비 +3",
                "strength": "기본 문제 정확도와 계산 안정감이 좋습니다.",
                "weakness": "문장형 조건 해석에서 시간이 조금 더 걸렸습니다.",
                "plan": "조건을 구조화해 읽는 연습을 짧게 반복하면 좋습니다.",
                "weak_concepts": ["문장형 조건 해석"],
            },
            "report": {
                "summary": "전반적으로 안정적인 학습 흐름을 보였고, 문제 읽기 전략만 보완하면 더 효율적으로 점수를 올릴 수 있는 상태입니다.",
                "attitude": "수업 태도는 안정적이었고 지시를 잘 따랐습니다.",
                "achievement": "그래프 해석과 계산은 전반적으로 잘 수행했습니다.",
                "homework": "숙제 수행은 성실한 편이었습니다.",
                "difficulty": "문장이 길어진 문제에서 조건 해석 속도가 다소 느렸습니다.",
                "test": "88점으로 안정적인 점수를 유지했고 계산 실수는 적었습니다.",
                "next_step": "다음 시간에는 긴 문장 문제를 구조화해서 읽는 연습을 진행할 예정입니다.",
                "message_draft": (
                    "안녕하세요. 지후는 오늘 수업에서 개념 이해와 계산은 안정적이었습니다. 다만 문장이 긴 문제에서 조건을 읽는 "
                    "속도가 조금 느려, 다음 시간에는 조건 분해 연습을 함께 진행하겠습니다."
                ),
            },
            "profile": {
                "state": "안정 유지",
                "summary": "전반적으로 안정적이며 큰 흔들림은 없습니다. 긴 문장 문제를 빠르게 읽는 전략이 붙으면 더 좋아질 수 있습니다.",
                "tags": ["안정적", "계산 정확", "문장제 속도", "숙제 성실"],
            },
            "timeline": [
                {
                    "date": "04.04",
                    "title": "일차함수 그래프 해석",
                    "body": "기본 개념은 잘 수행했고 긴 문장 조건에서 시간이 길어졌습니다.",
                },
                {
                    "date": "04.02",
                    "title": "함수 값 찾기",
                    "body": "계산 실수 없이 안정적으로 마무리했습니다.",
                },
                {
                    "date": "03.29",
                    "title": "좌표평면 복습",
                    "body": "문장제 해석 속도 보완 포인트가 보였습니다.",
                },
            ],
            "communication": [
                {"date": "04.04", "title": "수업 후 전달", "body": "긴 문장 문제 읽기 전략 보완 안내"},
                {"date": "03.30", "title": "과제 점검", "body": "숙제 이행 안정적이라고 전달"},
            ],
        },
    ],
}


def ensure_academy_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ACADEMY_DB_PATH.exists():
        payload = json.dumps(DEFAULT_ACADEMY_DATA, ensure_ascii=False, indent=2)
        ACADEMY_DB_PATH.write_text(payload, encoding="utf-8")
    if not ACADEMY_LOCK_PATH.exists():
        ACADEMY_LOCK_PATH.touch()


@contextmanager
def advisory_file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as lock_file:
        if msvcrt is not None:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        elif fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        try:
            yield
        finally:
            if msvcrt is not None:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            elif fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def read_academy_data_unlocked() -> dict[str, Any]:
    try:
        raw = ACADEMY_DB_PATH.read_text(encoding="utf-8-sig")
        payload = json.loads(raw) if raw.strip() else deepcopy(DEFAULT_ACADEMY_DATA)
    except (OSError, json.JSONDecodeError):
        payload = deepcopy(DEFAULT_ACADEMY_DATA)
    return merge_with_defaults(payload)


def write_academy_data_unlocked(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = merge_with_defaults(payload)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(ACADEMY_DB_PATH.parent),
        delete=False,
        suffix=".tmp",
    ) as handle:
        json.dump(normalized, handle, ensure_ascii=False, indent=2)
        temp_path = handle.name

    os.replace(temp_path, ACADEMY_DB_PATH)
    return normalized


@contextmanager
def academy_data_transaction() -> Iterator[dict[str, Any]]:
    ensure_academy_storage()
    with ACADEMY_THREAD_LOCK:
        with advisory_file_lock(ACADEMY_LOCK_PATH):
            payload = read_academy_data_unlocked()
            yield payload
            write_academy_data_unlocked(payload)


def load_academy_data() -> dict[str, Any]:
    ensure_academy_storage()
    with ACADEMY_THREAD_LOCK:
        return read_academy_data_unlocked()


def save_academy_data(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_academy_storage()
    with ACADEMY_THREAD_LOCK:
        with advisory_file_lock(ACADEMY_LOCK_PATH):
            return write_academy_data_unlocked(payload)


def get_academy_bootstrap() -> dict[str, Any]:
    payload = load_academy_data()
    classes = payload.get("classes", [])
    students = payload.get("students", [])
    class_map = {item["id"]: item for item in classes if item.get("id")}
    selected_class_id = payload.get("selected_class_id") or (classes[0]["id"] if classes else "")
    selected_class = class_map.get(selected_class_id) or (classes[0] if classes else {})

    class_students = [student for student in students if student.get("class_id") == selected_class.get("id")]
    if not class_students:
        class_students = students[:]

    selected_student_id = payload.get("selected_student_id") or (class_students[0]["id"] if class_students else "")
    selected_student = next(
        (student for student in class_students if student.get("id") == selected_student_id),
        class_students[0] if class_students else None,
    )

    timeline = build_timeline(classes, students)
    weak_concepts = build_weak_concepts(class_students)
    test_scores = [int(student.get("test", {}).get("score_value", 0)) for student in class_students if student.get("test")]

    completed_count = sum(1 for student in class_students if student.get("status") == "done")
    test_queue_count = sum(1 for item in classes if item.get("status") == "test_queue")
    report_queue_count = sum(1 for student in students if student.get("status") in {"pending", "care"})

    return {
        "academy": payload.get("academy", {}),
        "dashboard": {
            "metrics": [
                {
                    "label": "오늘 수업",
                    "value": f"{len(classes)}타임",
                    "detail": "중등 2타임, 고등 1타임 기준 시안",
                },
                {
                    "label": "작성 진행률",
                    "value": f"{completed_count}/{len(class_students)}",
                    "detail": f"{selected_class.get('name', '선택 반')} 학생 기준 완료 현황",
                },
                {
                    "label": "테스트 분석",
                    "value": f"{test_queue_count}건",
                    "detail": "단원 테스트 후 분석 대기",
                },
                {
                    "label": "학부모 전달",
                    "value": f"{report_queue_count}건",
                    "detail": "검토 후 PDF 또는 메시지 전달 예정",
                },
            ],
            "timeline": timeline,
            "outputs": payload.get("auto_outputs", []),
            "notes": payload.get("dashboard_notes", []),
            "selected_class": {
                "id": selected_class.get("id", ""),
                "name": selected_class.get("name", ""),
                "unit_name": selected_class.get("unit_name", ""),
                "schedule_label": selected_class.get("schedule_label", ""),
                "completion_text": f"{completed_count}/{len(class_students)} 완료" if class_students else "학생 데이터 없음",
            },
        },
        "workspace": {
            "selected_student_id": selected_student.get("id", "") if selected_student else "",
            "students": class_students,
            "test_overview": {
                "unit_name": selected_class.get("unit_name", "단원 테스트"),
                "average_score": round(sum(test_scores) / len(test_scores)) if test_scores else 0,
                "top_score": max(test_scores) if test_scores else 0,
                "retest_count": sum(1 for score in test_scores if score < 80),
                "score_rows": [
                    {
                        "student_id": student.get("id", ""),
                        "name": student.get("name", ""),
                        "score_label": student.get("test", {}).get("score_label", "-"),
                        "trend_label": student.get("test", {}).get("trend_label", "-"),
                    }
                    for student in class_students
                ],
                "weak_concepts": weak_concepts,
            },
        },
    }


def update_selected_student(student_id: str) -> dict[str, Any]:
    with academy_data_transaction() as payload:
        student_ids = {student.get("id", "") for student in payload.get("students", [])}
        if student_id and student_id in student_ids:
            payload["selected_student_id"] = student_id
        return merge_with_defaults(payload)


def update_student_lesson(
    *,
    student_id: str,
    natural_note: str,
    achievement: str,
    homework: str,
    difficulty: str,
    next_step: str,
    tags: list[str],
) -> dict[str, Any]:
    with academy_data_transaction() as payload:
        students = payload.get("students", [])
        updated_student: dict[str, Any] | None = None
        for student in students:
            if student.get("id") != student_id:
                continue

            lesson = dict(student.get("lesson", {}) or {})
            normalized_tags = normalize_tags(tags)
            homework_text = str(homework or "").strip()

            lesson.update(
                {
                    "natural_note": str(natural_note or "").strip(),
                    "achievement": str(achievement or "").strip(),
                    "homework": homework_text,
                    "homework_mini": extract_homework_mini(homework_text),
                    "difficulty": str(difficulty or "").strip(),
                    "next_step": str(next_step or "").strip(),
                    "tags": normalized_tags,
                    "updated_at": utc_now(),
                }
            )
            student["lesson"] = lesson
            student["status"] = derive_student_status(student.get("status", ""), lesson)
            student["status_label"] = derive_status_label(student["status"])
            student["status_copy"] = build_status_copy(lesson)
            updated_student = student
            payload["selected_student_id"] = student_id
            break

        if updated_student is None:
            raise KeyError(student_id)

        return deepcopy(updated_student)


def update_student_test(
    *,
    student_id: str,
    score_value: int,
    trend_label: str,
    strength: str,
    weakness: str,
    plan: str,
    weak_concepts: list[str],
) -> dict[str, Any]:
    with academy_data_transaction() as payload:
        students = payload.get("students", [])
        updated_student: dict[str, Any] | None = None
        for student in students:
            if student.get("id") != student_id:
                continue

            test = dict(student.get("test", {}) or {})
            normalized_score = max(0, min(100, int(score_value)))
            normalized_trend = str(trend_label or "").strip()
            normalized_strength = str(strength or "").strip()
            normalized_weakness = str(weakness or "").strip()
            normalized_plan = str(plan or "").strip()
            normalized_concepts = normalize_weak_concepts(weak_concepts)

            test.update(
                {
                    "score_value": normalized_score,
                    "score_label": build_score_label(normalized_score),
                    "trend_label": normalized_trend or "변동 없음",
                    "strength": normalized_strength,
                    "weakness": normalized_weakness,
                    "plan": normalized_plan,
                    "weak_concepts": normalized_concepts,
                    "updated_at": utc_now(),
                }
            )
            student["test"] = test

            report = dict(student.get("report", {}) or {})
            report["test"] = build_report_test_text(
                score_label=test["score_label"],
                trend_label=test["trend_label"],
                weakness=normalized_weakness,
                plan=normalized_plan,
            )
            if normalized_plan:
                report["next_step"] = normalized_plan
            student["report"] = report

            updated_student = student
            payload["selected_student_id"] = student_id
            break

        if updated_student is None:
            raise KeyError(student_id)

        return deepcopy(updated_student)


def update_student_report(
    *,
    student_id: str,
    summary: str,
    attitude: str,
    achievement: str,
    homework: str,
    difficulty: str,
    test: str,
    next_step: str,
    message_draft: str,
) -> dict[str, Any]:
    with academy_data_transaction() as payload:
        students = payload.get("students", [])
        updated_student: dict[str, Any] | None = None
        for student in students:
            if student.get("id") != student_id:
                continue

            report = dict(student.get("report", {}) or {})
            lesson = dict(student.get("lesson", {}) or {})
            normalized_message = compact_text(message_draft)
            updated_at = utc_now()

            report.update(
                {
                    "summary": compact_text(summary),
                    "attitude": compact_text(attitude),
                    "achievement": compact_text(achievement),
                    "homework": compact_text(homework),
                    "difficulty": compact_text(difficulty),
                    "test": compact_text(test),
                    "next_step": compact_text(next_step),
                    "message_draft": normalized_message,
                    "updated_at": updated_at,
                }
            )
            lesson["parent_message"] = normalized_message
            lesson["updated_at"] = updated_at
            student["report"] = report
            student["lesson"] = lesson

            updated_student = student
            payload["selected_student_id"] = student_id
            break

        if updated_student is None:
            raise KeyError(student_id)

        return deepcopy(updated_student)


def generate_student_report_draft(*, student_id: str) -> dict[str, Any]:
    with academy_data_transaction() as payload:
        students = payload.get("students", [])
        updated_student: dict[str, Any] | None = None
        for student in students:
            if student.get("id") != student_id:
                continue

            generated_report = build_generated_report(student)
            report = dict(student.get("report", {}) or {})
            lesson = dict(student.get("lesson", {}) or {})
            updated_at = utc_now()

            report.update(generated_report)
            report["updated_at"] = updated_at
            report["generated_at"] = updated_at
            lesson["parent_message"] = generated_report.get("message_draft", "")
            lesson["updated_at"] = updated_at

            student["report"] = report
            student["lesson"] = lesson
            updated_student = student
            payload["selected_student_id"] = student_id
            break

        if updated_student is None:
            raise KeyError(student_id)

        return deepcopy(updated_student)


def merge_with_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_ACADEMY_DATA)
    merged.update(payload or {})
    merged["academy"] = {**DEFAULT_ACADEMY_DATA["academy"], **(payload.get("academy", {}) if isinstance(payload, dict) else {})}
    return merged


def normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in tags:
        tag = str(item or "").strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized[:6]


def normalize_weak_concepts(concepts: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in concepts:
        label = str(item or "").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(label)
    return normalized[:5]


def build_score_label(score_value: int) -> str:
    return f"{max(0, min(100, int(score_value)))}점"


def build_report_test_text(*, score_label: str, trend_label: str, weakness: str, plan: str) -> str:
    parts = [score_label.strip() or "점수 미입력"]
    if trend_label.strip():
        parts.append(trend_label.strip())
    if weakness.strip():
        parts.append(f"보완 포인트는 {weakness.strip()}입니다.")
    if plan.strip():
        parts.append(f"다음에는 {plan.strip()} 중심으로 진행할 예정입니다.")
    return " ".join(parts).strip()


def build_generated_report(student: dict[str, Any]) -> dict[str, str]:
    lesson = dict(student.get("lesson", {}) or {})
    test = dict(student.get("test", {}) or {})
    tags = normalize_tags(list(lesson.get("tags", []) or []))

    summary = build_report_summary_text(
        achievement=lesson.get("achievement", ""),
        difficulty=lesson.get("difficulty", ""),
        next_step=coalesce_text(test.get("plan", ""), lesson.get("next_step", "")),
    )
    attitude = build_report_attitude_text(
        tags=tags,
        homework=lesson.get("homework", ""),
        difficulty=lesson.get("difficulty", ""),
    )
    achievement_text = build_report_achievement_text(
        achievement=lesson.get("achievement", ""),
        strength=test.get("strength", ""),
    )
    homework_text = build_report_homework_text(lesson.get("homework", ""))
    difficulty_text = build_report_difficulty_text(
        difficulty=lesson.get("difficulty", ""),
        weakness=test.get("weakness", ""),
        weak_concepts=test.get("weak_concepts", []),
    )
    test_text = build_report_test_text(
        score_label=compact_text(test.get("score_label", "")),
        trend_label=compact_text(test.get("trend_label", "")),
        weakness=compact_text(test.get("weakness", "")),
        plan=compact_text(test.get("plan", "")),
    )
    next_step = build_report_next_step_text(
        lesson_next_step=lesson.get("next_step", ""),
        test_plan=test.get("plan", ""),
    )
    message_draft = build_parent_message_draft(
        student_name=student.get("name", ""),
        achievement=lesson.get("achievement", ""),
        homework=lesson.get("homework", ""),
        difficulty=lesson.get("difficulty", ""),
        test_score_label=test.get("score_label", ""),
        test_trend_label=test.get("trend_label", ""),
        next_step=coalesce_text(test.get("plan", ""), lesson.get("next_step", "")),
    )

    return {
        "summary": summary,
        "attitude": attitude,
        "achievement": achievement_text,
        "homework": homework_text,
        "difficulty": difficulty_text,
        "test": test_text,
        "next_step": next_step,
        "message_draft": message_draft,
    }


def build_report_summary_text(*, achievement: str, difficulty: str, next_step: str) -> str:
    sentences: list[str] = []
    normalized_achievement = compact_text(achievement)
    normalized_difficulty = compact_text(difficulty)
    normalized_next_step = compact_text(next_step)

    if normalized_achievement:
        sentences.append(f"이번 수업에서는 {normalized_achievement} 흐름이 확인되었습니다.")
    if normalized_difficulty:
        sentences.append(f"특히 {normalized_difficulty} 부분은 추가 보완이 필요합니다.")
    if normalized_next_step:
        sentences.append(f"다음 시간에는 {normalized_next_step} 중심으로 연결할 예정입니다.")

    if sentences:
        return " ".join(sentences)
    return "이번 수업 내용을 바탕으로 다음 학습 계획을 안정적으로 이어갈 예정입니다."


def build_report_attitude_text(*, tags: list[str], homework: str, difficulty: str) -> str:
    normalized_homework = compact_text(homework)
    normalized_difficulty = compact_text(difficulty)
    tag_preview = ", ".join(tags[:3])

    caution = normalized_difficulty or any(
        any(keyword in tag for keyword in ("미완", "보완", "누락", "주의", "어려"))
        for tag in tags
    )
    positive = any(
        any(keyword in tag for keyword in ("완료", "집중", "질문", "이해", "성장", "안정"))
        for tag in tags
    )

    if caution:
        first_sentence = "수업 참여는 꾸준했지만 어려운 지점에서는 확인 질문과 반복 점검이 더 필요했습니다."
    elif positive:
        first_sentence = "수업 참여와 반응은 전반적으로 안정적이었고, 설명을 따라오는 흐름도 좋았습니다."
    else:
        first_sentence = "수업 참여 흐름은 전반적으로 안정적으로 유지되었습니다."

    sentences = [first_sentence]
    if tag_preview:
        sentences.append(f"이번 수업 관찰 키워드는 {tag_preview}입니다.")
    if normalized_homework:
        sentences.append(f"과제 진행 상태는 {normalized_homework}로 확인되었습니다.")
    return " ".join(sentences)


def build_report_achievement_text(*, achievement: str, strength: str) -> str:
    normalized_achievement = compact_text(achievement)
    normalized_strength = compact_text(strength)

    if normalized_achievement and normalized_strength:
        return f"{normalized_achievement} 상태이며, 테스트에서는 {normalized_strength}"
    if normalized_achievement:
        return f"{normalized_achievement} 상태로 확인되었습니다."
    if normalized_strength:
        return normalized_strength
    return "핵심 개념 이해 흐름을 현재 수업 데이터 기준으로 계속 점검하고 있습니다."


def build_report_homework_text(homework: str) -> str:
    normalized_homework = compact_text(homework)
    if normalized_homework:
        return f"숙제는 {normalized_homework} 상태로 확인되었습니다."
    return "숙제 진행 상태는 다음 수업 시작 전에 다시 점검할 예정입니다."


def build_report_difficulty_text(*, difficulty: str, weakness: str, weak_concepts: list[str]) -> str:
    normalized_difficulty = compact_text(difficulty)
    normalized_weakness = compact_text(weakness)
    concept_labels = normalize_weak_concepts(list(weak_concepts or []))
    sentences: list[str] = []

    if normalized_difficulty:
        sentences.append(f"{normalized_difficulty} 부분에서 어려움이 관찰되었습니다.")
    if concept_labels:
        sentences.append(f"테스트 기준 약한 개념은 {', '.join(concept_labels[:3])}입니다.")
    if normalized_weakness:
        sentences.append(normalized_weakness)

    if sentences:
        return " ".join(sentences)
    return "어려운 개념은 현재까지 큰 이슈 없이 진행 중이며, 세부 약점은 계속 추적하겠습니다."


def build_report_next_step_text(*, lesson_next_step: str, test_plan: str) -> str:
    focus = coalesce_text(test_plan, lesson_next_step)
    if focus:
        return f"다음 수업에서는 {focus} 중심으로 보완할 예정입니다."
    return "다음 수업에서는 현재 수업 메모를 바탕으로 취약 포인트를 다시 확인할 예정입니다."


def build_parent_message_draft(
    *,
    student_name: str,
    achievement: str,
    homework: str,
    difficulty: str,
    test_score_label: str,
    test_trend_label: str,
    next_step: str,
) -> str:
    normalized_name = compact_text(student_name) or "학생"
    normalized_achievement = compact_text(achievement)
    normalized_homework = compact_text(homework)
    normalized_difficulty = compact_text(difficulty)
    normalized_next_step = compact_text(next_step)
    normalized_score = compact_text(test_score_label)
    normalized_trend = compact_text(test_trend_label)

    sentences = [f"안녕하세요. {normalized_name} 학생 수업 내용 공유드립니다."]
    if normalized_achievement:
        sentences.append(f"이번 수업에서는 {normalized_achievement} 흐름이 확인되었습니다.")
    if normalized_homework:
        sentences.append(f"숙제는 {normalized_homework} 상태로 확인되었습니다.")
    if normalized_difficulty:
        sentences.append(f"어려워한 부분은 {normalized_difficulty}입니다.")
    if normalized_score:
        score_sentence = normalized_score
        if normalized_trend:
            score_sentence = f"{score_sentence}, {normalized_trend}"
        sentences.append(f"테스트는 {score_sentence}로 확인되었습니다.")
    if normalized_next_step:
        sentences.append(f"다음 수업에서는 {normalized_next_step} 중심으로 보완하겠습니다.")
    return " ".join(sentences)


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def coalesce_text(*values: Any) -> str:
    for value in values:
        normalized = compact_text(value)
        if normalized:
            return normalized
    return ""


def extract_homework_mini(homework_text: str) -> str:
    normalized = str(homework_text or "").strip()
    if not normalized:
        return "-"

    if "%" in normalized:
        return normalized

    return normalized[:20]


def derive_student_status(current_status: str, lesson: dict[str, Any]) -> str:
    note = str(lesson.get("natural_note", "")).strip()
    homework = str(lesson.get("homework", "")).strip()
    difficulty = str(lesson.get("difficulty", "")).strip()

    if not note:
        return "pending"
    if current_status == "care":
        return "care"
    if "미완료" in homework or "40%" in homework or "어려" in difficulty:
        return "care"
    return "done"


def derive_status_label(status: str) -> str:
    if status == "care":
        return "보완 필요"
    if status == "pending":
        return "작성 중"
    return "기록 완료"


def build_status_copy(lesson: dict[str, Any]) -> str:
    achievement = str(lesson.get("achievement", "")).strip()
    difficulty = str(lesson.get("difficulty", "")).strip()
    next_step = str(lesson.get("next_step", "")).strip()
    homework = str(lesson.get("homework", "")).strip()

    if achievement and next_step:
        return f"{achievement}. 다음 시간은 {next_step} 중심으로 보완합니다."
    if difficulty:
        return f"{difficulty} 부분을 중심으로 기록했습니다."
    if homework:
        return f"숙제 상태는 {homework}로 기록되었습니다."
    return "학생별 수업 메모가 저장되었습니다."


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def build_timeline(classes: list[dict[str, Any]], students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for lesson_class in classes:
        class_students = [student for student in students if student.get("class_id") == lesson_class.get("id")]
        pending_count = sum(1 for student in class_students if student.get("status") != "done")
        active = lesson_class.get("status") == "live"

        if active:
            summary = (
                f"{lesson_class.get('unit_name', '수업 진행 중')}, "
                f"{pending_count}명 기록 남음"
            )
        elif lesson_class.get("status") == "test_queue":
            summary = f"{lesson_class.get('unit_name', '테스트')}, 분석 대기"
        elif lesson_class.get("status") == "report_queue":
            summary = f"{lesson_class.get('unit_name', '학부모 전달')}, 결과지 검토 필요"
        else:
            summary = lesson_class.get("unit_name", "운영 대기")

        timeline.append(
            {
                "time": lesson_class.get("schedule_time", ""),
                "name": lesson_class.get("name", ""),
                "summary": summary,
                "active": active,
            }
        )
    return timeline


def build_weak_concepts(students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for student in students:
        for concept in student.get("test", {}).get("weak_concepts", []):
            label = str(concept or "").strip()
            if not label:
                continue
            counts[label] = counts.get(label, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    highest = ranked[0][1] if ranked else 1

    return [
        {
            "label": label,
            "count": count,
            "fill_percent": max(18, round((count / highest) * 100)),
        }
        for label, count in ranked[:3]
    ]
