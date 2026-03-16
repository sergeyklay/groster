# Stage 1: builder — install dependencies and project via uv
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: runtime — minimal production image
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/groster /app/groster
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

ENV PATH="/app/.venv/bin:$PATH"
ENV GROSTER_DATA_PATH=/app/data
ENV GROSTER_LOG_DIR=/app/logs
ENV GROSTER_LOG_FORMAT=json

RUN groupadd --gid 1000 groster && \
    useradd --uid 1000 --gid groster --shell /bin/sh --create-home groster && \
    mkdir -p /app/data /app/logs && chown groster:groster /app/data /app/logs

USER groster

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost',5000),2); s.close()"

LABEL org.opencontainers.image.title="groster" \
    org.opencontainers.image.description="WoW guild roster tool with alt detection" \
    org.opencontainers.image.url="https://github.com/sergeyklay/groster" \
    org.opencontainers.image.source="https://github.com/sergeyklay/groster" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.version="0.5.0"

ENTRYPOINT ["groster"]
CMD ["serve", "--host", "0.0.0.0", "--port", "5000"]
