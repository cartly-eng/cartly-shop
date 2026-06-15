# syntax=docker/dockerfile:1.7
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p -m 0700 /root/.ssh && ssh-keyscan github.com >> /root/.ssh/known_hosts
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=ssh pip install --no-cache-dir -r requirements.txt
COPY shop ./shop
ARG APP_VERSION=dev
ARG GIT_COMMIT=unknown
ENV APP_VERSION=${APP_VERSION} GIT_COMMIT=${GIT_COMMIT} PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.source="https://github.com/prateekkanurkar-cmd/cartly-shop" \
      org.opencontainers.image.version=${APP_VERSION} \
      org.opencontainers.image.revision=${GIT_COMMIT}
USER 10001
CMD ["python", "-m", "shop.main"]
