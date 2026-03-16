# Vercel Deploy Guide

이 프로젝트는 Vercel 배포 기준으로 맞춰져 있습니다.

## 필요한 환경변수

- `OPENAI_API_KEY`
- `BLOB_READ_WRITE_TOKEN`
- `LESSON_JOURNAL_BASIC_AUTH_USER`
- `LESSON_JOURNAL_BASIC_AUTH_PASSWORD`

## 배포 순서

1. GitHub에 이 저장소를 올립니다.
2. Vercel에서 저장소를 Import 합니다.
3. 위 환경변수 4개를 Vercel Project Settings에 넣습니다.
4. Deploy 합니다.

## 중요한 점

- 기록 데이터와 원본 음성 보관은 `Vercel Blob`에 저장됩니다.
- 앱 첫 화면은 `vercel.json`에서 `/static/index.html`로 연결됩니다.
- API는 `/api/config`, `/api/lessons`, `/api/lesson?id=...`, `/api/regenerate?id=...` 구조를 사용합니다.

## 업로드 제한

Vercel Functions 요청 크기 제한 때문에 큰 음성 파일은 업로드가 어려울 수 있습니다.

- 짧은 수업 음성이나 압축된 mp3 사용을 권장합니다.
- 긴 녹음은 나눠서 올리거나 전사문 직접 입력을 함께 고려하세요.
