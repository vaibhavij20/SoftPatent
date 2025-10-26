# Backend Dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source
COPY . /app

# Expose default port
EXPOSE 8001

# Optional: pick up .env at runtime
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
