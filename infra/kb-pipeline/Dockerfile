FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY data/sources.yaml ./data/sources.yaml
COPY data/coverage_matrix.yaml ./data/coverage_matrix.yaml
COPY data/manual ./data/manual
COPY ontology ./ontology

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/ingest.py"]
