FROM astral/uv:python3.14-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 appuser \
    && useradd -m -u 1000 -g appuser appuser

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project --no-dev

COPY --chown=appuser:appuser . /app

RUN uv sync --locked --no-dev

USER appuser

EXPOSE 8001

CMD ["uv", "run", "server.py"]
