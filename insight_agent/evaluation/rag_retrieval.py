"""Isolated vector and BM25 retrieval adapters using project runtime components."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

from dbgpt.core import Chunk
from dbgpt.rag.embedding import HuggingFaceEmbeddings
from dbgpt.rag.text_splitter.text_splitter import RecursiveCharacterTextSplitter
from dbgpt_ext.storage.full_text.elasticsearch import ElasticDocumentStore
from dbgpt_ext.storage.vector_store.chroma_store import ChromaStore, ChromaVectorConfig
from dbgpt_ext.storage.vector_store.elastic_store import ElasticsearchStoreConfig

DOCUMENT_TITLE = re.compile(r"^#\s+(.+)$", re.M)
SECTION_HEADING = re.compile(r"^#{2,3}\s+((?:\d+\.)+\s*[^\n]+|\d+\.\s*[^\n]+)$", re.M)
SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)")


def load_corpus(paths: Iterable[Path]) -> list[tuple[Path, str]]:
    documents: list[tuple[Path, str]] = []
    for root in paths:
        for path in sorted(root.glob("*.md")):
            documents.append((path, path.read_text(encoding="utf-8")))
    return documents


def build_chunks(
    corpus_paths: Iterable[Path], *, chunk_size: int, chunk_overlap: int
) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )
    chunks: list[Chunk] = []
    for path, content in load_corpus(corpus_paths):
        title_match = DOCUMENT_TITLE.search(content)
        title = title_match.group(1).strip() if title_match else path.stem
        status = "obsolete" if "已废止" in content or "旧版" in path.stem else "active"
        for section, section_text in _markdown_sections(content):
            prefix = f"《{path.name}》 {section}\n"
            parts = splitter.split_text(prefix + section_text)
            for index, part in enumerate(parts, start=1):
                digest = hashlib.sha256(
                    f"{path.name}|{section}|{index}|{chunk_size}|{chunk_overlap}".encode()
                ).hexdigest()[:24]
                chunks.append(
                    Chunk(
                        chunk_id=f"w3-{digest}",
                        content=part,
                        metadata={
                            "document": path.name,
                            "document_title": title,
                            "section": section,
                            "status": status,
                            "source_kind": "distractor"
                            if "rag_distractors" in str(path)
                            else "policy",
                            "chunk_index": index,
                        },
                    )
                )
    return chunks


def prepare_store(
    *,
    retriever: str,
    chunks: list[Chunk],
    index_name: str,
    vector_path: Path,
    embedding: HuggingFaceEmbeddings | None = None,
    elasticsearch_url: str = "127.0.0.1",
    elasticsearch_port: str = "9200",
) -> Any:
    """Build one isolated index and return the initialized store.

    Indexing once per run is important: loading the same deterministic chunk IDs for
    every question would both distort latency and create duplicate records.
    """
    if retriever == "vector":
        if embedding is None:
            raise ValueError("Vector retrieval requires an embedding model")
        store = ChromaStore(
            vector_store_config=ChromaVectorConfig(persist_path=str(vector_path)),
            name=index_name,
            embedding_fn=embedding,
        )
        store.load_document(chunks)
    elif retriever == "bm25":
        config = ElasticsearchStoreConfig(
            uri=elasticsearch_url,
            port=elasticsearch_port,
            user="",
            password="",
        )
        store = ElasticDocumentStore(config, name=index_name)
        store.load_document(chunks)
    else:
        raise ValueError(f"Unsupported retriever: {retriever}")
    return store


def search_store(
    *,
    retriever: str,
    store: Any,
    query: str,
    top_k: int,
    query_strategy: str = "single",
) -> list[dict[str, Any]]:
    queries = [query] if query_strategy == "single" else decompose_query(query)
    fetch_k = max(top_k, 8) if len(queries) > 1 else top_k
    result_lists: list[list[Any]] = []
    for subquery in queries:
        if retriever == "vector":
            found = store.similar_search_with_scores(subquery, fetch_k, 0.0)
        elif retriever == "bm25":
            found = store.full_text_search(subquery, fetch_k)
        else:
            raise ValueError(f"Unsupported retriever: {retriever}")
        result_lists.append(found)
    if len(result_lists) == 1:
        ranked_items = result_lists[0][:top_k]
    else:
        base = result_lists[0]
        expansion_slots = 2 if top_k >= 5 else 1
        keep = max(1, top_k - expansion_slots)
        ranked_items = list(base[:keep])
        seen = {item.chunk_id for item in ranked_items}
        seen_documents = {item.metadata.get("document") for item in ranked_items}
        expansion_candidates: dict[str, tuple[float, Any]] = {}
        for candidates in result_lists[1:]:
            for candidate_rank, item in enumerate(candidates, start=1):
                if (
                    item.chunk_id in seen
                    or item.metadata.get("document") in seen_documents
                    or item.metadata.get("status") != "active"
                    or item.metadata.get("source_kind") != "policy"
                ):
                    continue
                score, _ = expansion_candidates.get(item.chunk_id, (0.0, item))
                expansion_candidates[item.chunk_id] = (
                    score + 1.0 / (60 + candidate_rank),
                    item,
                )
        for _, novel in sorted(
            expansion_candidates.values(), key=lambda pair: pair[0], reverse=True
        ):
            document = novel.metadata.get("document")
            if novel.chunk_id in seen or document in seen_documents:
                continue
            ranked_items.append(novel)
            seen.add(novel.chunk_id)
            seen_documents.add(document)
            if len(ranked_items) >= top_k:
                break
        for item in base[keep:]:
            if len(ranked_items) >= top_k:
                break
            if item.chunk_id not in seen:
                ranked_items.append(item)
                seen.add(item.chunk_id)
    return [
        {
            "rank": rank,
            "chunk_id": item.chunk_id,
            "content": item.content,
            "score": round(1.0 / (60 + rank), 8),
            "document": item.metadata.get("document"),
            "section": item.metadata.get("section"),
            "status": item.metadata.get("status"),
            "source_kind": item.metadata.get("source_kind"),
        }
        for rank, item in enumerate(ranked_items, start=1)
    ]


def decompose_query(query: str) -> list[str]:
    """Create deterministic subqueries for Chinese multi-intent questions."""
    candidates = [query.strip()]
    clauses = [item.strip(" ，,；;。？?") for item in re.split(r"[，,；;。？?]", query)]
    subclauses: list[str] = []
    for clause in clauses:
        if len(clause) >= 4:
            candidates.append(clause)
        for item in re.split(r"并且|以及|并|且|和|分别", clause):
            item = item.strip(" ，,；;。？?")
            if len(item) >= 4:
                candidates.append(item)
                subclauses.append(item)
    if clauses:
        context = clauses[0]
        for item in subclauses:
            if item not in context:
                candidates.append(f"{context} {item}")
    unique: list[str] = []
    for item in candidates:
        if item and item not in unique:
            unique.append(item)
    return unique[:12]


def embedding_model(
    model_name: str, cache_folder: str | None = None
) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=model_name,
        cache_folder=cache_folder,
        model_kwargs={"device": "cpu", "local_files_only": True},
        encode_kwargs={"normalize_embeddings": True},
    )


def index_fingerprint(
    *,
    retriever: str,
    chunk_size: int,
    chunk_overlap: int,
    corpus_hash: str,
    run_id: str,
) -> str:
    digest = hashlib.sha256(
        f"{retriever}|{chunk_size}|{chunk_overlap}|{corpus_hash}|{run_id}".encode()
    ).hexdigest()[:16]
    return f"insight-w3-{retriever}-{chunk_size}-{chunk_overlap}-{digest}"


def _markdown_sections(content: str) -> list[tuple[str, str]]:
    matches = list(SECTION_HEADING.finditer(content))
    if not matches:
        return [("文档", content)]
    sections: list[tuple[str, str]] = []
    preamble = content[: matches[0].start()].strip()
    if preamble:
        sections.append(("文档信息", preamble))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        heading = match.group(1).strip()
        number = SECTION_NUMBER.match(heading)
        section = number.group(1) if number else heading
        body = content[start:end].strip()
        sections.append((section, f"{match.group(0)}\n{body}".strip()))
    return sections
