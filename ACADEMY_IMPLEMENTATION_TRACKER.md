# Academy Implementation Tracker

## Goal

수학학원 운영용 웹앱을 아래 흐름으로 순차 구축한다.

1. 학원 도메인 데이터 구조
2. 선생님 수업 후 입력 화면
3. 단원 테스트 분석
4. 학부모 결과지 / 메시지 생성
5. PDF 자동 생성

## Phase Status

### Phase 1. 도메인 데이터 뼈대와 기본 운영 셸

상태: 완료

구현 내용:

- 학원 운영용 샘플 데이터 저장 구조 추가
- `academy-ui` 프로토타입 전용 API 추가
- 화면 시안이 하드코딩이 아니라 서버 데이터 기반으로 렌더링되도록 연결
- 반/학생/수업 상태/테스트/결과지 미리보기 데이터 구조 정의

검수 내용:

- Python 문법 검사 완료
- academy bootstrap API 데이터 로드 확인
- 프론트엔드 JS 문법 검사 완료
- 로컬 데이터 파일 자동 생성 확인

주요 파일:

- `lesson_journal/academy.py`
- `lesson_journal/app.py`
- `static/academy-ui.html`
- `static/academy-ui.css`
- `static/academy-ui.js`

### Phase 2. 수업 후 입력 저장 기능

상태: 완료

구현 내용:

- 반 선택 / 학생 선택 상태를 실제 데이터에 연결
- 학생별 자연어 메모 저장 API
- 숙제 여부, 성취도, 어려운 부분 구조 저장
- 저장 후 다시 열었을 때 그대로 이어쓰기 가능하게 구성

검수 포인트:

- 학생별 메모가 섞이지 않는지
- 모바일에서 저장 동선이 편한지
- 저장 후 새로고침해도 유지되는지

### Phase 3. 테스트 분석 저장 기능

상태: 완료

구현 내용:

- 단원별 점수 입력
- 약한 개념 태그 저장
- 학생별 분석 코멘트 저장

검수 포인트:

- 저장 후 학생별 점수 반영
- 평균/최고점/재시험 필요 인원 재계산
- 약한 개념 집계가 다시 계산되는지 확인
- 결과지 테스트 문구가 함께 갱신되는지 확인

### Phase 4. 학부모 결과지 생성

상태: 완료

구현 내용:

- 수업 기록 + 테스트 결과를 합쳐 결과지 초안 생성 API 추가
- 결과지 각 섹션 직접 수정 및 저장 기능 추가
- 학부모 메시지 초안 복사 기능 추가
- 저장 시 결과지와 수업 메모의 학부모 전달 문구 동기화

검수 포인트:

- 초안 생성 후 결과지 미리보기가 바로 갱신되는지
- 결과지 수동 수정 후 새로고침해도 유지되는지
- 메시지 초안과 수업 메모의 학부모 전달 문구가 일치하는지

### Phase 5. PDF 생성

상태: 완료

구현 내용:

- 학부모 결과지 PDF 생성 모듈 추가
- A4 기준의 2단 카드형 결과지 레이아웃 구성
- 상단 버튼과 결과지 탭에서 PDF 다운로드 가능하도록 연결
- 생성한 PDF를 `output/pdf`에 함께 저장하는 규칙 추가
- 배포 환경을 고려한 폰트 탐색 경로와 임시 저장 경로 fallback 추가
- PDF 파일명에 시각과 고유 토큰을 붙여 덮어쓰기 방지

검수 포인트:

- 한국어 글꼴이 깨지지 않는지
- PDF 다운로드 전 현재 결과지 수정값이 먼저 저장되는지
- 실제 렌더링 이미지 기준으로 여백, 카드 배치, 페이지 나눔이 자연스러운지
- 반복 생성 시 PDF 파일이 덮어써지지 않는지

## Validation Log

- Phase 1 Python compile: passed
- Phase 1 bootstrap payload smoke test: passed
- Phase 1 frontend syntax check: passed
- Phase 2 Python compile: passed
- Phase 2 frontend syntax check: passed
- Phase 2 lesson save round-trip test: passed
- Phase 3 Python compile: passed
- Phase 3 frontend syntax check: passed
- Phase 3 test analysis round-trip and overview recompute: passed
- Phase 4 Python compile: passed
- Phase 4 frontend syntax check: passed
- Phase 4 report generate/save round-trip test: passed
- Phase 5 Python compile: passed
- Phase 5 frontend syntax check: passed
- Phase 5 PDF generation and file save: passed
- Phase 5 PDF visual review via rendered PNG: passed
- Hardening concurrent academy save smoke test: passed
- Hardening unique PDF filename test: passed
