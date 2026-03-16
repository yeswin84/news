@echo off
cd /d "%~dp0"

set REPO_URL=
for /f "tokens=2" %%a in ('git remote get-url origin 2^>nul') do set REPO_URL=%%a

if not defined REPO_URL (
  echo Enter your GitHub repository URL.
  echo Example: https://github.com/yourname/lesson-journal-app.git
  set /p REPO_URL=Repo URL: 
)

git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%

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
