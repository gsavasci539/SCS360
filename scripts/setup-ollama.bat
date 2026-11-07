@echo off
echo ========================================
echo Ollama Setup for SCS360
echo ========================================
echo.

echo Starting Ollama container...
docker-compose -f docker-compose.ollama.yml up -d

echo.
echo Waiting for Ollama to start...
timeout /t 10 /nobreak

echo.
echo Pulling llama3.2 model...
docker exec scs360-ollama ollama pull llama3.2

echo.
echo ========================================
echo Ollama setup complete!
echo ========================================
echo.
echo Ollama is running at: http://localhost:11434
echo Model: llama3.2
echo.
echo To stop Ollama: docker-compose -f docker-compose.ollama.yml down
echo To view logs: docker-compose -f docker-compose.ollama.yml logs -f
echo.
pause
