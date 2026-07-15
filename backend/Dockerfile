# ================================================
# Stage 1: Build & Dependency Installation
# ================================================
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Create a virtual environment and place it in the PATH
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 2. Install dependencies directly into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ================================================
# Stage 2: Minimal Runtime Environment
# ================================================
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV PORT=10000

# 3. Copy the fully built venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# 4. Ensure the runner stage uses the venv's binaries (like uvicorn)
ENV PATH="/opt/venv/bin:$PATH"

COPY . /app

# Create a non-root system user for security isolation
RUN useradd -u 10001 apiuser \
    && mkdir -p /app/secrets \
    && chown -R apiuser:apiuser /app

USER apiuser
EXPOSE 10000

# Uvicorn will now be found perfectly!
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]