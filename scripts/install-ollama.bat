@echo off
echo ========================================
echo Ollama Installation for SCS360
echo ========================================
echo.

echo Downloading Ollama installer...
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"

echo.
echo Installing Ollama...
start /wait "" "%TEMP%\OllamaSetup.exe"

echo.
echo Waiting for installation to complete...
timeout /t 30 /nobreak

echo.
echo Pulling llama3.2 model...
ollama pull llama3.2

echo.
echo Starting Ollama server...
start "" ollama serve

echo.
echo ========================================
echo Ollama installation complete!
echo ========================================
echo.
echo Ollama is running at: http://localhost:11434
echo Model: llama3.2
echo.
echo The Ollama server is running in a new window.
echo Keep that window open while using the chatbot.
echo.
pause
