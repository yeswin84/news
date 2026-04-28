# Lesson Journal App

수업 음성 파일을 올리면 전사, 수업 요약, 핵심 포인트, 개념 정리, 학생 기록을 한 번에 만드는 개인용 웹앱입니다. 여러 파일을 한 수업으로 묶어 처리하고, 노션용 마크다운 복사와 PDF 저장까지 지원합니다.

## 로컬 실행

1. [.env](C:/Users/sk012/Projects/lesson_journal_app/.env) 파일에 `OPENAI_API_KEY`를 넣습니다.
2. [start_lesson_journal.bat](C:/Users/sk012/Projects/lesson_journal_app/start_lesson_journal.bat)을 더블클릭합니다.
3. 브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000) 을 엽니다.

같은 와이파이의 휴대폰이나 다른 기기에서도 접속할 수 있습니다. 서버 실행 후 터미널에 표시되는 `Same Wi-Fi` 주소로 접속하면 됩니다.

## Vercel 배포

이 프로젝트는 Vercel 기준으로도 동작하도록 수정되어 있습니다.

필수 환경변수:

- `OPENAI_API_KEY`
- `BLOB_READ_WRITE_TOKEN`
- `LESSON_JOURNAL_BASIC_AUTH_USER`
- `LESSON_JOURNAL_BASIC_AUTH_PASSWORD`

자세한 내용은 [DEPLOY.md](C:/Users/sk012/Projects/lesson_journal_app/DEPLOY.md)를 보면 됩니다.

배포 후에는 Vercel이 발급한 링크를 카카오톡으로 바로 공유할 수 있습니다. Vercel 환경에서는 음성 파일을 브라우저에서 Blob으로 직접 올린 뒤, 서버가 전사만 처리하므로 큰 파일 업로드에도 더 안정적입니다.

## 추천 사용 순서

1. 음성 파일을 하나 이상 선택합니다.
2. `기록 만들기`를 누릅니다.
3. 결과가 나오면 `리포트 보기`, `요약`, `개념 정리`에서 확인합니다.
4. `전체 복사`를 눌러 노션에 붙여 넣습니다.
5. `PDF 저장`을 눌러 브라우저 인쇄 화면에서 PDF로 저장합니다.

## 참고

- `.env` 파일은 Git에 올라가지 않도록 설정되어 있습니다.
- 실제 수업 기록은 로컬 데이터 폴더에 저장되며, 원본 음성 파일은 기본적으로 보관하지 않습니다.
