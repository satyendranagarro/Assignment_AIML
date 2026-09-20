"""Graph store protocol: in-memory + Neo4j backends for ontology entities."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from dotenv import load_dotenv

from src.ontology.models import Entity
from src.rag.models import RetrievalHit

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass
class GraphStats:
    entity_count: int = 0
    relation_count: int = 0
    by_class: dict[str, int] = field(default_factory=dict)
    backend: str = "memory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "by_class": dict(self.by_class),
            "backend": self.backend,
        }


class GraphStore(Protocol):
    def load_entities(self, entities: list[Entity], *, reset: bool = True) -> GraphStats: ...

    def expand_from_query(
        self,
        query: str,
        *,
        seed_hits: list[RetrievalHit] | None = None,
        limit: int = 8,
    ) -> list[RetrievalHit]: ...

    def stats(self) -> GraphStats: ...

    def close(self) -> None: ...


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2}


class InMemoryGraphStore:
    """Deterministic offline graph for tests and Neo4j-unavailable smoke."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._adj: dict[str, list[tuple[str, str]]] = {}  # id -> [(rel, target)]

    def load_entities(self, entities: list[Entity], *, reset: bool = True) -> GraphStats:
        if reset:
            self._entities.clear()
            self._adj.clear()
        rel_count = 0
        for ent in entities:
            self._entities[ent.id] = ent
            edges = self._adj.setdefault(ent.id, [])
            for rel in ent.relations:
                edges.append((rel.type, rel.target))
                rel_count += 1
                # reverse adjacency for undirected-ish expand
                self._adj.setdefault(rel.target, []).append((f"rev_{rel.type}", ent.id))
        return self.stats()

    def stats(self) -> GraphStats:
        by_class: dict[str, int] = {}
        rels = 0
        for ent in self._entities.values():
            by_class[ent.class_] = by_class.get(ent.class_, 0) + 1
            rels += len(ent.relations)
        return GraphStats(
            entity_count=len(self._entities),
            relation_count=rels,
            by_class=by_class,
            backend="memory",
        )

    def _match_entities(self, query: str) -> list[Entity]:
        q = query.lower()
        qtoks = _tokens(query)
        scored: list[tuple[int, Entity]] = []
        for ent in self._entities.values():
            names = [ent.name, *ent.aliases]
            score = 0
            for name in names:
                if name.lower() in q:
                    score += 10
                elif _tokens(name) & qtoks:
                    score += 3
            if score:
                scored.append((score, ent))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [e for _, e in scored]

    def expand_from_query(
        self,
        query: str,
        *,
        seed_hits: list[RetrievalHit] | None = None,
        limit: int = 8,
    ) -> list[RetrievalHit]:
        seeds = self._match_entities(query)
        # Also pull entity ids from chroma metadata
        if seed_hits:
            for hit in seed_hits:
                raw = str((hit.metadata or {}).get("entity_ids") or "")
                for eid in raw.split(","):
                    eid = eid.strip()
                    if eid and eid in self._entities:
                        seeds.append(self._entities[eid])

        seen: set[str] = set()
        hits: list[RetrievalHit] = []
        for ent in seeds:
            if ent.id in seen:
                continue
            seen.add(ent.id)
            evidence = ent.evidence[0] if ent.evidence else None
            hits.append(
                RetrievalHit(
                    text=_entity_text(ent),
                    score=0.55,
                    source="neo4j",
                    title=ent.name,
                    url=evidence.url if evidence else "",
                    doc_id=evidence.doc_id if evidence else "",
                    source_id=evidence.source_id if evidence else "",
                    entity_id=ent.id,
                    entity_class=ent.class_,
                    relation_path=[],
                    metadata={"name": ent.name, "tags": ",".join(ent.tags)},
                )
            )
            # one-hop neighbors
            for rel_type, target in self._adj.get(ent.id, []):
                if target in seen or target not in self._entities:
                    continue
                if rel_type.startswith("rev_"):
                    continue
                neighbor = self._entities[target]
                seen.add(target)
                nev = neighbor.evidence[0] if neighbor.evidence else None
                hits.append(
                    RetrievalHit(
                        text=_entity_text(neighbor),
                        score=0.45,
                        source="neo4j",
                        title=neighbor.name,
                        url=nev.url if nev else "",
                        doc_id=nev.doc_id if nev else "",
                        source_id=nev.source_id if nev else "",
                        entity_id=neighbor.id,
                        entity_class=neighbor.class_,
                        relation_path=[f"{ent.id}-[{rel_type}]->{neighbor.id}"],
                        metadata={"name": neighbor.name, "via": ent.id},
                    )
                )
                if len(hits) >= limit:
                    return hits[:limit]
            if len(hits) >= limit:
                break
        return hits[:limit]

    def close(self) -> None:
        return None


def _entity_text(ent: Entity) -> str:
    parts = [f"{ent.class_}: {ent.name}"]
    if ent.tags:
        parts.append("tags=" + ",".join(ent.tags))
    if ent.relations:
        rels = "; ".join(f"{r.type}->{r.target}" for r in ent.relations[:6])
        parts.append("relations: " + rels)
    if ent.evidence:
        parts.append(ent.evidence[0].snippet)
    return " | ".join(parts)


class Neo4jGraphStore:
    """Load ontology entities into Neo4j and expand via Cypher."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        load_dotenv()
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password if password is not None else os.getenv("NEO4J_PASSWORD", "")
        if not self.password:
            raise RuntimeError("NEO4J_PASSWORD is required for Neo4jGraphStore")
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self._driver.verify_connectivity()

    def close(self) -> None:
        self._driver.close()

    def load_entities(self, entities: list[Entity], *, reset: bool = True) -> GraphStats:
        with self._driver.session() as session:
            if reset:
                session.run("MATCH (n:KBEntity) DETACH DELETE n")
            for ent in entities:
                session.run(
                    """
                    MERGE (e:KBEntity {id: $entity_id})
                    SET e.name = $name,
                        e.class = $entity_class,
                        e.aliases = $aliases,
                        e.tags = $tags,
                        e.spot_checked = $spot_checked
                    """,
                    entity_id=ent.id,
                    name=ent.name,
                    entity_class=ent.class_,
                    aliases=list(ent.aliases),
                    tags=list(ent.tags),
                    spot_checked=ent.spot_checked,
                )
                for rel in ent.relations:
                    session.run(
                        """
                        MATCH (a:KBEntity {id: $src})
                        MATCH (b:KBEntity {id: $tgt})
                        MERGE (a)-[r:REL {type: $rtype}]->(b)
                        """,
                        src=ent.id,
                        tgt=rel.target,
                        rtype=rel.type,
                    )
                for ev in ent.evidence[:3]:
                    session.run(
                        """
                        MATCH (e:KBEntity {id: $entity_id})
                        MERGE (d:KBDoc {doc_id: $doc_id})
                        SET d.url = $url, d.source_id = $source_id, d.snippet = $snippet
                        MERGE (e)-[:EVIDENCED_IN]->(d)
                        """,
                        entity_id=ent.id,
                        doc_id=ev.doc_id,
                        url=ev.url,
                        source_id=ev.source_id,
                        snippet=ev.snippet[:500],
                    )
        return self.stats()

    def stats(self) -> GraphStats:
        with self._driver.session() as session:
            ent_count = session.run("MATCH (e:KBEntity) RETURN count(e) AS c").single()["c"]
            rel_count = session.run("MATCH ()-[r:REL]->() RETURN count(r) AS c").single()["c"]
            rows = session.run(
                "MATCH (e:KBEntity) RETURN e.class AS class, count(*) AS c"
            )
            by_class = {r["class"]: r["c"] for r in rows}
        return GraphStats(
            entity_count=int(ent_count),
            relation_count=int(rel_count),
            by_class=by_class,
            backend="neo4j",
        )

    def expand_from_query(
        self,
        query: str,
        *,
        seed_hits: list[RetrievalHit] | None = None,
        limit: int = 8,
    ) -> list[RetrievalHit]:
        # Name / alias CONTAINS match + optional one-hop
        q = query.strip()
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (e:KBEntity)
                WHERE toLower(e.name) CONTAINS toLower($q)
                   OR any(a IN e.aliases WHERE toLower(a) CONTAINS toLower($q))
                OPTIONAL MATCH (e)-[r:REL]->(n:KBEntity)
                OPTIONAL MATCH (e)-[:EVIDENCED_IN]->(d:KBDoc)
                RETURN e, collect(DISTINCT {rel: r.type, neighbor: n})[0..5] AS neighbors,
                       collect(DISTINCT d)[0..1] AS docs
                LIMIT $limit
                """,
                q=q,
                limit=limit,
            )
            hits: list[RetrievalHit] = []
            for row in rows:
                e = row["e"]
                docs = row["docs"] or []
                doc = docs[0] if docs else None
                hits.append(
                    RetrievalHit(
                        text=f"{e.get('class')}: {e.get('name')}",
                        score=0.55,
                        source="neo4j",
                        title=e.get("name") or "",
                        url=(doc.get("url") if doc else "") or "",
                        doc_id=(doc.get("doc_id") if doc else "") or "",
                        source_id=(doc.get("source_id") if doc else "") or "",
                        entity_id=e.get("id") or "",
                        entity_class=e.get("class") or "",
                        metadata={"tags": ",".join(e.get("tags") or [])},
                    )
                )
                for item in row["neighbors"] or []:
                    n = item.get("neighbor")
                    if not n:
                        continue
                    hits.append(
                        RetrievalHit(
                            text=f"{n.get('class')}: {n.get('name')}",
                            score=0.45,
                            source="neo4j",
                            title=n.get("name") or "",
                            url="",
                            entity_id=n.get("id") or "",
                            entity_class=n.get("class") or "",
                            relation_path=[
                                f"{e.get('id')}-[{item.get('rel')}]->{n.get('id')}"
                            ],
                        )
                    )
                    if len(hits) >= limit:
                        return hits[:limit]
        # Fallback: if CONTAINS on full query failed, try tokens via memory-like seed from hits
        if not hits and seed_hits:
            # No extra work; return empty
            return []
        return hits[:limit]


def open_graph_store(*, prefer_neo4j: bool = True, force_memory: bool = False) -> GraphStore:
    """Open Neo4j when configured and reachable; else in-memory."""
    if force_memory:
        return InMemoryGraphStore()
    if not prefer_neo4j:
        return InMemoryGraphStore()
    load_dotenv()
    password = os.getenv("NEO4J_PASSWORD") or ""
    if not password:
        return InMemoryGraphStore()
    try:
        return Neo4jGraphStore()
    except Exception:
        return InMemoryGraphStore()
