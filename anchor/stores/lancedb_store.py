from pathlib import Path
from typing import Any, Optional
import lancedb
import pyarrow as pa
from anchor.config import settings

# PyArrow schema for 1024-d BGE-M3 embeddings and chunk metadata
LANCEDB_CHUNKS_SCHEMA = pa.schema(
    [
        pa.field("chunk_id", pa.string()),
        pa.field("doc_id", pa.string()),
        pa.field("schedule_no", pa.int32()),
        pa.field("section", pa.string()),
        pa.field("page_no", pa.int32()),
        pa.field("bbox", pa.list_(pa.float32())),
        pa.field("text", pa.string()),
        pa.field("sha256", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), 1024)),
    ]
)


_LANCEDB_TABLE_CACHE: dict[tuple[str, str], lancedb.table.Table] = {}


def clear_lancedb_cache() -> None:
    """Clear cached LanceDB table connections."""
    _LANCEDB_TABLE_CACHE.clear()


def get_lancedb_connection(db_dir: Optional[Path] = None) -> lancedb.DBConnection:
    """Connect to embedded LanceDB directory."""
    target_dir = db_dir or settings.LANCEDB_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(target_dir))


def init_lancedb_table(
    db_dir: Optional[Path] = None, table_name: str = "regulatory_chunks"
) -> lancedb.table.Table:
    """Initialize or open the regulatory chunks table with 1024-d PyArrow schema."""
    target_dir = db_dir or settings.LANCEDB_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_key = (str(target_dir.resolve()), table_name)

    if cache_key in _LANCEDB_TABLE_CACHE:
        try:
            _ = len(_LANCEDB_TABLE_CACHE[cache_key])
            return _LANCEDB_TABLE_CACHE[cache_key]
        except Exception:
            _LANCEDB_TABLE_CACHE.pop(cache_key, None)

    db = get_lancedb_connection(target_dir)
    try:
        tables_res = db.list_tables()
        existing_tables = getattr(tables_res, "tables", list(tables_res))
    except Exception:
        try:
            existing_tables = db.table_names()
        except Exception:
            existing_tables = []

    if table_name in existing_tables:
        tbl = db.open_table(table_name)
    else:
        tbl = db.create_table(table_name, schema=LANCEDB_CHUNKS_SCHEMA)

    _LANCEDB_TABLE_CACHE[cache_key] = tbl
    return tbl


def insert_chunks(
    chunks: list[dict[str, Any]],
    db_dir: Optional[Path] = None,
    table_name: str = "regulatory_chunks",
) -> int:
    """Insert chunk records into LanceDB."""
    if not chunks:
        return 0
    table = init_lancedb_table(db_dir, table_name)
    table.add(chunks)
    return len(chunks)


def query_vector(
    vector: list[float],
    top_k: int = 10,
    db_dir: Optional[Path] = None,
    table_name: str = "regulatory_chunks",
) -> list[dict[str, Any]]:
    """Query nearest neighbor vector embeddings."""
    table = init_lancedb_table(db_dir, table_name)
    results = table.search(vector).limit(top_k).to_list()
    return results


def count_chunks(
    db_dir: Optional[Path] = None, table_name: str = "regulatory_chunks"
) -> int:
    """Return total count of chunks indexed in the table."""
    table = init_lancedb_table(db_dir, table_name)
    return len(table)
