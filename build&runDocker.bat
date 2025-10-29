@echo off
SET IMAGE_NAME=backend_api
SET PORT=8000

echo Building Docker image...
docker build -t %IMAGE_NAME% .

IF %ERRORLEVEL% NEQ 0 (
    echo Docker build failed. Exiting.
    exit /b 1
)

echo Running Docker container...
docker run --rm -p %PORT%:%PORT% %IMAGE_NAME%

pause
