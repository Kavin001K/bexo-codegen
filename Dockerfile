FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-unifont \
    fonts-liberation \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Use system Chromium (Playwright browser download fails on Debian Trixie in Cloud Build)
ENV CHROME_PATH=/usr/bin/chromium
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && npm install -g lighthouse@12.6.0

COPY src/ ./src/

ENV PYTHONPATH=/app
ENV PORT=8080
ENV RUN_LIGHTHOUSE=true

EXPOSE 8080

CMD ["python", "src/main.py"]
