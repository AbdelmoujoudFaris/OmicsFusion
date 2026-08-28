FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="OmicsFusion"
LABEL org.opencontainers.image.description="Modular multi-omics analysis and integration platform"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/omicsfusion

# System dependencies (R is optional; the container works fully in Python-only mode)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        r-base \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install ".[gui,dev]"

COPY . .

RUN pip install -e .

ENTRYPOINT ["omicsfusion"]
CMD ["--help"]
