@echo off
cd /d "%~dp0"

echo This script publishes only to GitHub.
echo To commit, push, and deploy to Vercel together, use publish_reading_note.bat.
echo.

set REPO_URL=
for /f "delims=" %%a in ('git remote get-url origin 2^>nul') do set REPO_URL=%%a

if not defined REPO_URL (
  echo Enter your GitHub repository URL.
  echo Example: https://github.com/yourname/lesson-journal-app.git
  set /p REPO_URL=Repo URL: 
)

git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%

echo.
echo Staging and committing current changes...
git add .
git diff --cached --quiet
if errorlevel 1 (
  set /p COMMIT_MSG=Commit message: 
  if not defined COMMIT_MSG set COMMIT_MSG=Update Reading Note app
  git commit -m "%COMMIT_MSG%"
)

echo.
echo Pushing to GitHub...
git push -u origin main

echo.
if errorlevel 1 (
  echo Push failed. Check the repository URL and GitHub login.
) else (
  echo Push completed.
)
pause
