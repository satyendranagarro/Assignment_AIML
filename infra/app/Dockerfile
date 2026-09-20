FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY mcp_servers ./mcp_servers
COPY app ./app
COPY ontology ./ontology
COPY data/sources.yaml ./data/sources.yaml
COPY data/coverage_matrix.yaml ./data/coverage_matrix.yaml

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
