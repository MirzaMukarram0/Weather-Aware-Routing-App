FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8080
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120"]
