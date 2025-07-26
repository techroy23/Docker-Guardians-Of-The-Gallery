# syntax=docker/dockerfile:1.4

############################################
# 1) Builder Stage: compile native deps & install packages
############################################
FROM python:3.11-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       gcc libjpeg-dev zlib1g-dev wget \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

############################################
# 2) Runtime Stage: minimal image
############################################
FROM python:3.11-slim

# Install tini for proper signal handling
RUN apt-get update \
  && apt-get install -y --no-install-recommends tini wget \
  && rm -rf /var/lib/apt/lists/*

# Copy Python libs from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

# Prepare upload folder, fix ownership and declare volume
RUN mkdir -p data

# Mount point for persistent uploads
VOLUME ["/app/data"]

# Expose application port
EXPOSE 3001

# Default environment (override at runtime)
ENV FLASK_ENV=production \
    COOKIE_TIMEOUT=300 \
    PYTHONUNBUFFERED=1

# Use tini to reap zombie processes
ENTRYPOINT ["/usr/bin/tini", "--"]

# Healthcheck for basic liveness
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3001/login || exit 1

# Launch Gunicorn
# CMD ["gunicorn", "app:app", "-b", "0.0.0.0:3001", "-w", "4", "--log-level", "info"]
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:3001", "-w", "4", "--reload", "--log-level", "debug"]

