FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser && mkdir -p /app/uploads /app/private_uploads && chown -R appuser:appuser /app
USER appuser
EXPOSE 5006
CMD ["python", "scripts/start_server.py"]
