# Vercel Deploy Guide

이 프로젝트는 Vercel에 올린 뒤 링크를 바로 공유해 쓸 수 있게 구성되어 있습니다.

## 필요한 환경변수

- `OPENAI_API_KEY`
- `BLOB_READ_WRITE_TOKEN`
- `LESSON_JOURNAL_BASIC_AUTH_USER`
- `LESSON_JOURNAL_BASIC_AUTH_PASSWORD`

마지막 두 개는 선택입니다. 비워두면 누구나 링크로 바로 접속할 수 있습니다.

## 배포 순서

### 가장 빠른 방법: CLI로 바로 배포

1. 이 폴더에서 `npx vercel login` 으로 로그인합니다.
2. `npx vercel` 로 첫 배포를 연결합니다.
3. 환경변수는 Vercel 안내에 따라 입력하거나 Dashboard에서 넣습니다.
4. 최종 공개 링크는 `npx vercel --prod` 로 발급합니다.

### GitHub 연동 방식

1. GitHub에 이 저장소를 올립니다.
2. Vercel에서 저장소를 Import 합니다.
3. Project Settings > Environment Variables에 환경변수를 넣습니다.
4. Deploy 합니다.
5. 발급된 Vercel URL을 카카오톡으로 보내면 바로 접속할 수 있습니다.

## 현재 배포 구조

- 첫 화면은 `vercel.json`에서 `/static/index.html`로 연결됩니다.
- Python API는 `/api/config`, `/api/lessons`, `/api/lesson?id=...`, `/api/regenerate?id=...` 를 사용합니다.
- Vercel 배포에서는 `/api/upload-audio`가 브라우저 업로드용 토큰을 발급합니다.
- 음성 파일은 브라우저에서 Vercel Blob으로 직접 올라가고, 서버는 그 파일을 읽어 전사한 뒤 업로드된 원본을 바로 삭제합니다.
- 최종적으로 남는 것은 텍스트 기록 데이터뿐입니다.

## 왜 업로드 방식을 바꿨는가

Vercel Functions는 요청 본문 크기 제한이 있기 때문에, 큰 음성 파일을 함수로 직접 보내면 실패할 수 있습니다.

현재 구조는 이 문제를 피하기 위해 다음 흐름을 사용합니다.

1. 브라우저가 음성 파일을 Vercel Blob으로 직접 업로드
2. Python API가 Blob의 파일을 읽어 OpenAI로 전사
3. 전사 완료 후 업로드된 원본 오디오 삭제
4. 텍스트 기록만 저장

## 운영 팁

- 아드님이 링크만 눌러 바로 쓰게 하려면 인증 환경변수는 비워두는 쪽이 가장 편합니다.
- 외부 공개가 불안하면 Basic Auth를 켜고 아이디/비밀번호를 같이 전달하면 됩니다.
- 30분 이상 긴 파일은 압축된 `m4a`나 `mp3`가 더 안정적입니다.
- 같은 수업 파일을 여러 개로 나눠 올려도 한 수업으로 합쳐 처리됩니다.
