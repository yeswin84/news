# 학생 전용 링크형 버전 구현 순서

이 문서는 `lesson_journal_app`을 `학생 전용 링크 + 선생님 확인용 관리자 화면` 구조로 바꾸기 위한 실제 구현 순서를 정리한 작업 문서다.

목표는 다음과 같다.

- 기존 업로드, 전사, 생성, 저장 흐름은 최대한 유지한다.
- 학생별 데이터가 절대 섞이지 않게 만든다.
- 학생은 자기 링크만 열면 바로 사용할 수 있게 만든다.
- 선생님은 전체 학생 진행 상태를 한 번에 볼 수 있게 만든다.

## 1. 구현 원칙

이번 작업은 아래 순서로 진행하는 것이 가장 안전하다.

1. 학생 컨텍스트를 먼저 만든다.
2. 저장 경로를 학생별로 분리한다.
3. API를 학생 기준으로 제한한다.
4. 학생용 화면 문구와 흐름을 바꾼다.
5. 관리자 화면을 추가한다.
6. 마지막에 AI 출력 문구를 학생 자기주도형으로 조정한다.

이 순서를 지키는 이유는, UI를 먼저 바꾸면 화면은 그럴듯해 보여도 데이터가 섞일 수 있기 때문이다.

## 2. 단계별 구현 순서

### 단계 0. 기준점 확보

목적:

- 현재 버전이 어디까지 동작하는지 기준을 남긴다.

작업:

- 현재 앱이 로컬과 Vercel에서 정상 동작하는지 확인
- 음성 1개 업로드, 여러 개 업로드, PDF 저장, 문서 저장 확인
- 기존 데이터 구조 백업

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\WORKFLOW_REFERENCE.md`
- `C:\Users\sk012\Projects\lesson_journal_app\data\lessons.json`

완료 기준:

- 현재 개인용 버전이 문제없이 동작하는 상태를 확인했다.

### 단계 1. 학생 모델과 링크 규칙 확정

목적:

- 학생을 어떻게 식별할지 먼저 정한다.

권장 결정:

- 내부 식별자: `student_id`
- 링크 식별자: `student_slug`
- 표시 이름: `student_name`

권장 링크:

- 학생용: `/s/{student_slug}`
- 관리자용: `/admin`

작업:

- 학생 레코드 구조 확정
- slug 생성 규칙 정리
- 관리자 화면 접근 방식 정리

권장 학생 레코드 예시:

```json
{
  "student_id": "stu_001",
  "student_slug": "minji-7f3k2",
  "student_name": "민지",
  "status": "active",
  "created_at": "2026-03-17T09:00:00Z",
  "updated_at": "2026-03-17T09:00:00Z"
}
```

완료 기준:

- 학생을 URL로 식별하는 규칙이 확정되었다.

### 단계 2. 저장 구조를 학생별 namespace로 분리

목적:

- 데이터가 학생별로 절대 섞이지 않게 만든다.

가장 먼저 바꿔야 하는 부분이다.

작업:

- `storage.py`에 학생별 저장 prefix 추가
- lesson 저장/조회/삭제 함수가 `student_slug`를 받도록 변경
- 오디오 임시 저장도 학생별 경로로 분리

현재 구조:

- `lessons/{lesson_id}.json`
- `audio/{audio_id}.m4a`

변경 후 구조:

- `students/{student_slug}/lessons/{lesson_id}.json`
- `students/{student_slug}/audio/{audio_id}.m4a`

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\storage.py`

완료 기준:

- 같은 저장소를 써도 학생별로 레코드와 오디오 경로가 분리된다.

### 단계 3. 요청에서 학생 컨텍스트 판별

목적:

- 브라우저가 학생 id를 보내지 않아도 서버가 현재 학생을 알 수 있게 만든다.

작업:

- `app.py`에서 현재 요청 경로를 보고 학생 slug 추출
- `/s/{student_slug}` 형태를 처리할 라우팅 추가
- `GET /api/context` 추가
- 학생 링크로 들어오면 현재 학생 정보 반환

`/api/context` 예시:

```json
{
  "mode": "student",
  "student": {
    "student_slug": "minji-7f3k2",
    "student_name": "민지"
  },
  "summary": {
    "lesson_count": 3,
    "latest_lesson_date": "2026-03-17"
  }
}
```

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\app.py`
- 필요 시 `C:\Users\sk012\Projects\lesson_journal_app\vercel.json`

완료 기준:

- 학생 링크에서 접속하면 서버가 현재 학생을 정확히 식별한다.

### 단계 4. lesson API를 학생 단위로 잠그기

목적:

- 학생 링크에서 보이는 기록이 그 학생 것만 되게 만든다.

작업:

- `GET /api/lessons`는 현재 학생의 기록만 반환
- `POST /api/lessons`는 현재 학생 기록만 생성
- `GET /api/lesson?id=...`는 현재 학생 소유 기록만 조회
- `DELETE /api/lesson?id=...`도 현재 학생 소유 기록만 삭제

중요:

- 프론트가 `student_slug`를 body로 보내는 방식에 의존하지 않는다.
- 서버가 요청 컨텍스트를 기준으로 강제 분리한다.

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\app.py`
- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\storage.py`

완료 기준:

- 다른 학생 링크에서 다른 학생 기록 id를 넣어도 조회되지 않는다.

### 단계 5. 학생 목록 저장소 추가

목적:

- 관리자 화면과 학생 링크 발급을 위한 학생 목록을 만든다.

작업:

- 학생 목록 저장 구조 추가
- 학생 생성 함수 추가
- 학생 조회 함수 추가
- 학생별 최근 제출 상태 계산 함수 추가

권장 저장 구조:

- 로컬: `data/students/index.json`
- Blob: `students/index.json`

권장 필드:

- `student_slug`
- `student_name`
- `status`
- `lesson_count`
- `latest_lesson_date`

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\storage.py`

완료 기준:

- 관리자 화면에서 참조할 학생 목록 데이터가 준비된다.

### 단계 6. 학생용 화면을 자기주도형 리플렉션 앱으로 변경

목적:

- 기존 수업 기록 앱 느낌을 학생 개인 사용 흐름으로 바꾼다.

작업:

- 메인 헤드 카피 변경
- 학생 이름 표시 영역 추가
- 최근 제출 상태 표시
- 업로드 안내 문구를 학생 중심으로 변경
- 검색, 목록, 상세 문구를 자기기록형 문맥으로 수정

권장 문구 방향:

- `오늘 읽은 기사 기록하기`
- `내 생각 녹음하기`
- `내가 이해한 내용 정리`
- `다시 생각해볼 질문`

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\static\index.html`
- `C:\Users\sk012\Projects\lesson_journal_app\static\app.js`
- `C:\Users\sk012\Projects\lesson_journal_app\static\styles.css`

완료 기준:

- 학생이 보기에 “선생님 수업 기록 앱”이 아니라 “내 기사 리플렉션 앱”처럼 보인다.

### 단계 7. 관리자 화면 추가

목적:

- 선생님이 학생별 진행 여부를 한눈에 볼 수 있게 만든다.

권장 방식:

- 학생 화면과 분리된 `/admin` 페이지 추가

권장 구성:

- 학생 목록 카드
- 최근 제출 날짜
- 총 제출 수
- 최근 제목 또는 한 줄 소감
- 학생 링크 복사 버튼
- 학생 상세 보기 버튼

가능하면 새 파일로 분리:

- `C:\Users\sk012\Projects\lesson_journal_app\static\admin.html`
- `C:\Users\sk012\Projects\lesson_journal_app\static\admin.js`
- `C:\Users\sk012\Projects\lesson_journal_app\static\styles.css`

서버 작업:

- `GET /api/admin/students`
- `GET /api/admin/student-lessons?slug=...`

완료 기준:

- 선생님이 한 화면에서 각 학생의 진행 상태를 확인할 수 있다.

### 단계 8. AI 프롬프트와 결과 구조 조정

목적:

- 입력 음성이 `학생 혼자 말한 리플렉션`이어도 결과가 자연스럽게 나오게 만든다.

작업:

- `ai.py`의 system prompt 수정
- `teacher/student` 대화 중심 표현 축소
- `student_summary`의 의미를 자기주도형 기록으로 재정의
- notion export 문구 수정
- 리포트 섹션 제목을 학생 기준으로 수정

유지해도 좋은 구조:

- `summary_text`
- `summary_points`
- `concept_cards`
- `student_summary`
- `lesson_headline`

바꿔야 하는 것:

- 말투
- 안내 문구
- 섹션 제목
- 생성 기준 문장

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\ai.py`
- `C:\Users\sk012\Projects\lesson_journal_app\static\app.js`

완료 기준:

- 학생 혼자 녹음한 내용으로도 자연스러운 요약과 자기기록이 생성된다.

### 단계 9. 관리자 보호와 운영 편의 추가

목적:

- 선생님 화면은 보호하고, 학생 링크는 사용하기 쉽게 둔다.

작업:

- `/admin`만 보호하는 방식 검토
- 또는 관리자 전용 토큰 방식 추가
- 학생 링크 복사 기능 추가
- 학생 생성 절차 정리

주요 파일:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\app.py`
- `C:\Users\sk012\Projects\lesson_journal_app\DEPLOY.md`

완료 기준:

- 학생은 쉽게 접근하고, 선생님 관리자 화면은 보호된다.

### 단계 10. 실제 운영 테스트

목적:

- 데이터 분리와 관리자 흐름이 실제로 안전한지 검증한다.

테스트 시나리오:

1. 학생 A 링크로 기록 생성
2. 학생 B 링크로 기록 생성
3. 학생 A 링크에서 학생 B 기록이 안 보이는지 확인
4. 학생 B 링크에서 학생 A 기록이 안 보이는지 확인
5. 관리자 화면에서 A, B 둘 다 보이는지 확인
6. 최근 제출 날짜와 총 제출 수가 정확한지 확인
7. PDF 저장과 문서 저장이 여전히 정상인지 확인

완료 기준:

- 학생 간 데이터 혼선이 없고 관리자 화면도 정확히 동작한다.

## 3. 추천 작업 묶음

실제 작업은 아래 3개 묶음으로 진행하는 것이 좋다.

### 1차 묶음: 데이터 분리

- `storage.py`
- `app.py`
- 학생 컨텍스트
- 학생별 lesson API

이 단계가 끝나야 데이터 섞임 위험이 사라진다.

### 2차 묶음: 학생용 UI

- `index.html`
- `app.js`
- `styles.css`
- AI 문구 일부 조정

이 단계에서 학생이 실제로 사용할 수 있는 화면이 완성된다.

### 3차 묶음: 관리자 화면과 운영 가이드

- 관리자 API
- `admin.html`
- `admin.js`
- 배포/운영 문서

이 단계에서 선생님 운영성이 완성된다.

## 4. 지금 이 프로젝트 기준 우선 수정 파일

가장 먼저:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\storage.py`
- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\app.py`

그 다음:

- `C:\Users\sk012\Projects\lesson_journal_app\static\index.html`
- `C:\Users\sk012\Projects\lesson_journal_app\static\app.js`
- `C:\Users\sk012\Projects\lesson_journal_app\static\styles.css`

그 다음:

- `C:\Users\sk012\Projects\lesson_journal_app\lesson_journal\ai.py`

마지막:

- `C:\Users\sk012\Projects\lesson_journal_app\DEPLOY.md`
- 관리자 전용 정적 파일들

## 5. 바로 다음에 할 일

이 문서 다음 단계로 가장 자연스러운 작업은 아래 둘 중 하나다.

1. `학생 컨텍스트 + 학생별 저장 분리`부터 실제 코드 수정 시작
2. 먼저 `학생용 화면/관리자 화면 와이어프레임 문서`를 작성

실제로는 1번부터 시작하는 것이 맞다.

## 6. 한 줄 결론

이 프로젝트는 먼저 `학생별 데이터 분리`를 끝내고, 그 위에 `학생용 링크 화면`과 `선생님 관리자 화면`을 얹는 순서로 구현해야 가장 안전하다.
