FROM python:3.13-slim

# uv installs the locked dependencies. yt-dlp uses Deno as its JavaScript runtime for YouTube.
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
COPY --from=denoland/deno:bin-2.9.8 /deno /usr/local/bin/deno

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Dependencies come first, so a code change doesn't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

# uv installs the project in editable mode by default. Keep it that way: the code finds
# prompts/ and templates/ relative to its own location, which a built wheel would change.
COPY harness ./harness
COPY prompts ./prompts
COPY templates ./templates
RUN uv sync --locked --no-dev

# UID 1000 matches the usual first user on the host, who owns the mounted data and vault folders.
RUN useradd --uid 1000 --create-home harness \
    && mkdir /data /vault \
    && chown harness:harness /data /vault
USER harness

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# The exec form makes uvicorn PID 1, so it receives SIGTERM and can requeue a running job.
CMD ["uvicorn", "harness.api:app", "--host", "0.0.0.0", "--port", "8000"]
