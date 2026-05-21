FROM astral/uv:python3.14-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml /app/
RUN uv sync --no-dev --no-install-project

COPY scoreboard_app /app/scoreboard_app
RUN mkdir -p /app/data && chmod 0775 /app/data

ENV PATH="/app/.venv/bin:${PATH}"
ENV SCOREBOARD_DB_PATH=/app/data/scoreboard.db

EXPOSE 8000

CMD ["uvicorn", "scoreboard_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
