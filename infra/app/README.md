# Streamlit UI container — Phase 6 (optional)

```bash
# Ensure .env exists (copy from .env.example). Never commit secrets.
cp -n .env.example .env

docker compose -f infra/app/compose.yml --profile app up -d --build
# http://localhost:8501
```

For day-to-day work, run on the host instead:

```bash
streamlit run app/streamlit_app.py
```

The container mounts `data/` and `ontology/` so it can use the same Chroma path / Neo4j as Phase 4 load.
