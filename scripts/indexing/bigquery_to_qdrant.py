"""BigQuery → Qdrant indexing pipeline.

Usage:
    python scripts/indexing/bigquery_to_qdrant.py \
        --project PROJECT_ID --dataset DATASET --table TABLE

Options:
    --project   GCP project ID
    --dataset   BigQuery dataset name
    --table     BigQuery table name
    --batch     Embedding batch size (default: 100)
    --chunk-size    Max characters per review chunk (default: 300)
    --chunk-overlap Overlap characters between chunks (default: 100)
    --recreate  Drop and recreate the Qdrant collection before indexing
"""

import argparse
import hashlib
import logging
import os
import sys
import uuid
from typing import Any

from google.cloud import bigquery
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    KeywordIndexParams,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "restaurant_reviews")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
VECTOR_SIZE = 1536  # text-embedding-3-small


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks when it exceeds chunk_size."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def deterministic_uuid(restaurant_id: str, review_date: str, chunk_idx: int) -> str:
    """Generate a deterministic UUID5 for idempotent upserts."""
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    name = f"{restaurant_id}|{review_date}|{chunk_idx}"
    return str(uuid.uuid5(namespace, name))


def setup_collection(client: QdrantClient, recreate: bool) -> None:
    """Ensure the Qdrant collection exists with correct schema."""
    exists = client.collection_exists(COLLECTION_NAME)
    if exists and recreate:
        logger.info("Deleting existing collection '%s'", COLLECTION_NAME)
        client.delete_collection(COLLECTION_NAME)
        exists = False

    if not exists:
        logger.info("Creating collection '%s'", COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="restaurant_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Collection and payload indexes created.")
    else:
        logger.info("Collection '%s' already exists, skipping creation.", COLLECTION_NAME)


# ---------------------------------------------------------------------------
# BigQuery fetch
# ---------------------------------------------------------------------------

def fetch_reviews(
    project: str, dataset: str, table: str
) -> list[dict[str, Any]]:
    """Fetch all review rows from BigQuery."""
    client = bigquery.Client(project=project)
    query = f"""
        SELECT
            restaurant_id,
            review_text,
            source,
            rating,
            review_date,
            place_name
        FROM `{project}.{dataset}.{table}`
        WHERE review_text IS NOT NULL AND TRIM(review_text) != ''
    """
    logger.info("Fetching reviews from BigQuery: %s.%s.%s", project, dataset, table)
    rows = list(client.query(query).result())
    logger.info("Fetched %d rows.", len(rows))
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Embedding + upsert
# ---------------------------------------------------------------------------

def build_points(
    rows: list[dict[str, Any]],
    embeddings_model: OpenAIEmbeddings,
    chunk_size: int,
    chunk_overlap: int,
    batch_size: int,
) -> None:
    """Embed reviews in batches and upsert into Qdrant."""
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Expand rows into chunks
    chunks: list[tuple[str, dict[str, Any]]] = []
    for row in rows:
        text = row["review_text"]
        for idx, chunk in enumerate(chunk_text(text, chunk_size, chunk_overlap)):
            point_id = deterministic_uuid(
                str(row["restaurant_id"]),
                str(row.get("review_date", "")),
                idx,
            )
            payload = {
                "restaurant_id": str(row["restaurant_id"]),
                "source": str(row.get("source", "")),
                "rating": float(row["rating"]) if row.get("rating") is not None else None,
                "review_date": str(row.get("review_date", "")),
                "place_name": str(row.get("place_name", "")),
                "review_text": chunk,
            }
            chunks.append((point_id, payload, chunk))

    logger.info("Total chunks to index: %d", len(chunks))

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c[2] for c in batch]
        vectors = embeddings_model.embed_documents(texts)
        points = [
            PointStruct(id=c[0], vector=v, payload=c[1])
            for c, v in zip(batch, vectors)
        ]
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info("Upserted batch %d/%d (%d points)", i // batch_size + 1, -(-len(chunks) // batch_size), len(points))

    logger.info("Indexing complete.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index BigQuery reviews into Qdrant")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--dataset", required=True, help="BigQuery dataset")
    parser.add_argument("--table", required=True, help="BigQuery table")
    parser.add_argument("--batch", type=int, default=100, help="Embedding batch size")
    parser.add_argument("--chunk-size", type=int, default=300, help="Max chars per chunk")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Overlap chars")
    parser.add_argument("--recreate", action="store_true", help="Recreate Qdrant collection")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=openai_api_key,
    )

    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    setup_collection(qdrant, recreate=args.recreate)

    rows = fetch_reviews(args.project, args.dataset, args.table)
    if not rows:
        logger.warning("No rows fetched. Exiting.")
        return

    build_points(
        rows=rows,
        embeddings_model=embeddings_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        batch_size=args.batch,
    )


if __name__ == "__main__":
    main()
