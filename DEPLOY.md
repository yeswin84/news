# Deploy Guide

이 앱은 로컬 파일에 기록을 저장하므로, 퍼블리시할 때는 `지속 저장소(volume/disk)`가 있는 플랫폼을 권장합니다.

## 추천 방식

### 1. 가장 쉬운 방법: Railway

- 이 프로젝트에는 `Dockerfile`이 있어서 Railway가 바로 배포할 수 있습니다.
- 음성 기록과 `lessons.json`을 유지하려면 Volume을 붙여야 합니다.

권장 설정:

- `OPENAI_API_KEY`: 실제 OpenAI 키
- `LESSON_JOURNAL_DATA_DIR=/data`
- `LESSON_JOURNAL_BASIC_AUTH_USER=원하는아이디`
- `LESSON_JOURNAL_BASIC_AUTH_PASSWORD=원하는비밀번호`

Volume mount path:

- `/data`

## 배포 전 체크

- 외부 공개 전에는 반드시 Basic Auth를 설정하는 것을 권장합니다.
- 원본 음성을 오래 보관하지 않으려면 앱에서 `원본 음성 보관`을 기본적으로 끄고 사용하세요.
- 중요한 기록은 별도 백업을 권장합니다.

## 현재 앱이 배포용으로 맞춰진 부분

- `PORT` 환경변수를 자동 인식합니다.
- `0.0.0.0` 바인딩을 지원합니다.
- `/healthz` 경로를 제공합니다.
- 저장 위치를 `LESSON_JOURNAL_DATA_DIR`로 바꿀 수 있습니다.
- `LESSON_JOURNAL_BASIC_AUTH_USER/PASSWORD`로 전체 앱 보호가 가능합니다.
