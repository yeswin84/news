@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ==========================================
echo  Reading Note publish workflow
echo ==========================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo This folder is not a Git repository.
  pause
  exit /b 1
)

set "REPO_URL="
for /f "delims=" %%a in ('git remote get-url origin 2^>nul') do set "REPO_URL=%%a"

if not defined REPO_URL (
  echo GitHub remote is not connected yet.
  echo Create an empty GitHub repository first, then paste its URL here.
  echo Example: https://github.com/yourname/reading-note.git
  echo.
  set /p "REPO_URL=GitHub repository URL: "
  if not defined REPO_URL (
    echo Repository URL is required.
    pause
    exit /b 1
  )
  git remote add origin "!REPO_URL!"
  if errorlevel 1 (
    echo Failed to add GitHub remote.
    pause
    exit /b 1
  )
)

echo.
echo Remote:
git remote -v

echo.
echo Current changes:
git status --short

echo.
set /p "COMMIT_MSG=Commit message (press Enter for auto message): "
if not defined COMMIT_MSG (
  for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "NOW=%%a"
  set "COMMIT_MSG=Update Reading Note app !NOW!"
)

echo.
echo Staging changes...
git add .
if errorlevel 1 (
  echo Failed to stage changes.
  pause
  exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
  echo.
  echo Creating commit: !COMMIT_MSG!
  git commit -m "!COMMIT_MSG!"
  if errorlevel 1 (
    echo Commit failed.
    pause
    exit /b 1
  )
) else (
  echo.
  echo No new changes to commit.
)

echo.
echo Pushing to GitHub...
git push -u origin main
if errorlevel 1 (
  echo GitHub push failed. Check repository URL and GitHub login.
  pause
  exit /b 1
)

echo.
echo Deploying to Vercel production...
npx vercel --prod --yes
if errorlevel 1 (
  echo Vercel deploy failed. Check Vercel login and project settings.
  pause
  exit /b 1
)

echo.
echo Done. GitHub push and Vercel deploy completed.
pause
