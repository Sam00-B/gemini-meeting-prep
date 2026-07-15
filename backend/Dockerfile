# ================================================
# Stage 1: Build & Dependency Installation
# ================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Avoid writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if any library needs compiling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements into a local virtual env
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ================================================
# Stage 2: Minimal Runtime Environment
# ================================================
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV PORT=10000

# Copy installed packages from builder stage
COPY --from=builder /build/deps /usr/local/lib/python3.11/site-packages
COPY . /app

# Create a non-root system user for security isolation
RUN useradd -u 10001 apiuser \
    && mkdir -p /app/secrets \
    && chown -R apiuser:apiuser /app

# Switch to the secure non-root user
USER apiuser

# Render automatically maps its external port to the EXPOSE port
EXPOSE 10000

# Run Uvicorn using the exec form to ensure graceful termination signals (SIGTERM) are handled
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]