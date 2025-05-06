FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=supplier_ranking_service.settings

# Set work directory
WORKDIR /app

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install gunicorn

# Copy project
COPY . /app/

# Run database migrations and collect static files at build time
RUN python manage.py collectstatic --noinput

# Run as non-root user for better security
RUN useradd -m appuser
USER appuser

# Expose the application port
EXPOSE 8000

# Use gunicorn as the production server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "supplier_ranking_service.wsgi:application"]