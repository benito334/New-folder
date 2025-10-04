# syntax=docker/dockerfile:1
# Use official Playwright image with browsers & dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.39.0-jammy

# Install system deps for Playwright

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "backend.ingestion.instagram.monitor"]
