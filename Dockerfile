FROM python:3.12-slim

# -------------------------------------------------
# SYSTEM DEPENDENCIES (Postgres + Playwright)
# -------------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -------------------------------------------------
# PYTHON DEPS
# -------------------------------------------------
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------
# INSTALL PLAYWRIGHT CHROMIUM
# -------------------------------------------------
RUN python -m playwright install chromium

# -------------------------------------------------
# PROJECT FILES
# -------------------------------------------------
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
