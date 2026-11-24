FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY controller ./controller
COPY backend ./backend

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/backend/src

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "vyro_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
