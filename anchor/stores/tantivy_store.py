import re
from pathlib import Path
from typing import Any, Optional
import tantivy
from anchor.config import settings

_TANTIVY_INDEX_CACHE: dict[str, tantivy.Index] = {}


def clear_tantivy_cache() -> None:
    """Clear cached Tantivy index instances."""
    _TANTIVY_INDEX_CACHE.clear()


def build_tantivy_schema() -> tantivy.Schema:
    """Build the tantivy BM25 schema for regulatory documents."""
    builder = tantivy.SchemaBuilder()
    builder.add_text_field("chunk_id", stored=True)
    builder.add_text_field("doc_id", stored=True, tokenizer_name="raw")
    builder.add_text_field("section", stored=True, tokenizer_name="en_stem")
    builder.add_text_field("breadcrumb", stored=True, tokenizer_name="en_stem")
    builder.add_text_field("text", stored=True, tokenizer_name="en_stem")
    builder.add_unsigned_field("schedule_no", stored=True, indexed=True)
    builder.add_text_field("sha256", stored=True)
    return builder.build()


def get_or_create_tantivy_index(index_dir: Optional[Path] = None) -> tantivy.Index:
    """Get an existing tantivy index or create a new one, using cached singleton."""
    target_dir = index_dir or settings.TANTIVY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_key = str(target_dir.resolve())

    if cache_key in _TANTIVY_INDEX_CACHE:
        return _TANTIVY_INDEX_CACHE[cache_key]

    try:
        idx = tantivy.Index.open(str(target_dir))
    except Exception:
        schema = build_tantivy_schema()
        idx = tantivy.Index(schema, path=str(target_dir))

    _TANTIVY_INDEX_CACHE[cache_key] = idx
    return idx


def add_documents(
    documents: list[dict[str, Any]], index_dir: Optional[Path] = None
) -> int:
    """Add a list of documents to the tantivy BM25 index."""
    if not documents:
        return 0

    index = get_or_create_tantivy_index(index_dir)
    writer = index.writer()

    for doc_data in documents:
        doc = tantivy.Document()
        doc.add_text("chunk_id", str(doc_data.get("chunk_id", "")))
        doc.add_text("doc_id", str(doc_data.get("doc_id", "")))
        doc.add_text("section", str(doc_data.get("section", "")))
        doc.add_text("breadcrumb", str(doc_data.get("breadcrumb", "")))
        doc.add_text("text", str(doc_data.get("text", "")))
        doc.add_unsigned("schedule_no", int(doc_data.get("schedule_no", 0)))
        doc.add_text("sha256", str(doc_data.get("sha256", "")))
        writer.add_document(doc)

    writer.commit()
    index.reload()
    return len(documents)


def _clean_tantivy_query(query_str: str) -> str:
    """Escape or strip Tantivy special syntax characters to prevent parser errors."""
    cleaned = re.sub(r'[\+\-\(\)\{\}\[\]\^\*\?\:\\\/\~\"\!]', ' ', query_str)
    return ' '.join(cleaned.split()).strip()


def search_bm25(
    query_str: str, top_k: int = 10, index_dir: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Execute a BM25 sparse search query over the indexed text and breadcrumb fields."""
    if not query_str or not query_str.strip():
        return []

    index = get_or_create_tantivy_index(index_dir)
    searcher = index.searcher()

    try:
        query = index.parse_query(query_str, ["text", "breadcrumb", "section"])
    except Exception:
        cleaned_str = _clean_tantivy_query(query_str)
        if not cleaned_str:
            return []
        try:
            query = index.parse_query(cleaned_str, ["text", "breadcrumb", "section"])
        except Exception:
            return []

    search_result = searcher.search(query, top_k)
    hits = search_result.hits

    results = []
    for score, doc_address in hits:
        doc = searcher.doc(doc_address)
        doc_dict = doc.to_dict()
        # Flatten single-item lists for convenience
        item = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in doc_dict.items()}
        item["score"] = score
        results.append(item)

    return results


def count_documents(index_dir: Optional[Path] = None) -> int:
    """Return the total number of documents in the index."""
    index = get_or_create_tantivy_index(index_dir)
    return index.searcher().num_docs
