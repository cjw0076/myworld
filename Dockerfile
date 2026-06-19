FROM python:3.12-slim

# Non-root user — UID/GID 1000 matches default Linux user convention.
RUN groupadd --gid 1000 aios && \
    useradd --uid 1000 --gid 1000 --home /app --no-create-home aios

WORKDIR /app

# Copy the full repo (needed: launcher_relative_root() resolves relative to scripts/).
# Submodules excluded by .dockerignore; memoryOS absence = memory_hits=0, not a crash.
COPY --chown=aios:aios . .

# Install AIOS CLI — stdlib-only, no heavy PyPI deps.
RUN pip install --no-cache-dir -e .

USER aios

EXPOSE 8741

# Default: offline demo — works with no API key, no GPU, no network.
# For the serve UI: docker run -e GEMINI_API_KEY=... -p 8741:8741 <image> aios serve --host 0.0.0.0
CMD ["aios", "demo"]
