# Lesson Journal App

수업 음성 파일을 올리면 전사, 요약, 학생 버전 기록, 보호자 기록을 한 번에 만드는 개인용 웹앱입니다.

## 로컬 실행

1. [.env](C:/Users/sk012/Projects/lesson_journal_app/.env) 파일에 `OPENAI_API_KEY`를 넣습니다.
2. [start_lesson_journal.bat](C:/Users/sk012/Projects/lesson_journal_app/start_lesson_journal.bat)을 더블클릭합니다.
3. 브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000) 을 엽니다.

## Vercel 배포

이 프로젝트는 Vercel 기준으로도 동작하도록 수정되어 있습니다.

필수 환경변수:

- `OPENAI_API_KEY`
- `BLOB_READ_WRITE_TOKEN`
- `LESSON_JOURNAL_BASIC_AUTH_USER`
- `LESSON_JOURNAL_BASIC_AUTH_PASSWORD`

자세한 내용은 [DEPLOY.md](C:/Users/sk012/Projects/lesson_journal_app/DEPLOY.md)를 보면 됩니다.

## 추천 사용 순서

1. 음성 파일을 하나 이상 선택합니다.
2. `기록 만들기`를 누릅니다.
3. 결과가 나오면 `리포트 보기`에서 확인합니다.
4. `전체 복사`를 눌러 노션에 붙여 넣습니다.

## 참고

- `.env` 파일은 Git에 올라가지 않도록 설정되어 있습니다.
- 실제 수업 기록과 업로드 파일도 Git에 올라가지 않도록 제외되어 있습니다.
