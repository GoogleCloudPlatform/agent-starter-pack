# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ruff: noqa

from google_cloud_pipeline_components.types.artifact_types import BQTable
from kfp.dsl import Input, component


@component(
    base_image="us-docker.pkg.dev/production-ai-template/starter-pack/data_processing:0.2",
)
def ingest_data(
    project_id: str,
    location: str,
    collection_id: str,
    ingestion_batch_size: int,
    input_table: Input[BQTable],
    look_back_days: int = 7,
) -> None:
    """Ingest processed data into Vector Search 2.0 Collection.

    Uses a create-before-delete strategy for safe incremental updates:

    1. Read recent chunks from BigQuery (within look_back_days window).
    2. Query Vector Search for existing chunks matching the same question_ids.
    3. Separate chunks into three categories:
       - New: in BQ but not in VS (to create)
       - Unchanged: same chunk_id in both BQ and VS (skip)
       - Stale: in VS but not in current BQ batch (to delete)
       Chunk IDs include a run timestamp, so re-processed documents get
       new IDs that won't collide with existing ones.
    4. Create new chunks first.
    5. Delete stale chunks only after new ones are successfully created.

    This ordering guarantees no data loss window: if the pipeline fails
    after creating new chunks but before deleting stale ones, there will
    be temporary duplicates (harmless) rather than missing data. The next
    successful run will clean up any stale chunks.

    Args:
        project_id: Google Cloud project ID
        location: Vector Search location
        collection_id: Vector Search 2.0 Collection ID
        ingestion_batch_size: Number of data objects per batch request
        input_table: Input BQ table with processed chunks
        look_back_days: Number of days to look back for recent records
    """
    import logging
    from datetime import datetime, timedelta, timezone

    import bigframes.pandas as bpd
    from google.cloud import vectorsearch_v1beta

    # Initialize logging
    logging.basicConfig(level=logging.INFO)

    # Initialize clients
    logging.info("Initializing clients...")
    bpd.options.bigquery.project = project_id
    bpd.options.bigquery.location = location

    data_object_client = vectorsearch_v1beta.DataObjectServiceClient()
    search_client = vectorsearch_v1beta.DataObjectSearchServiceClient()
    collection_path = (
        f"projects/{project_id}/locations/{location}/collections/{collection_id}"
    )
    logging.info("Clients initialized.")

    dataset = input_table.metadata["datasetId"]
    table = input_table.metadata["tableId"]

    cutoff = (datetime.now(timezone.utc) - timedelta(days=look_back_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    query = f"""
        SELECT
            question_id
            , full_text_md
            , text_chunk
            , chunk_id
        FROM {project_id}.{dataset}.{table}
        WHERE creation_timestamp >= DATETIME("{cutoff}")
    """
    df = bpd.read_gbq(query).to_pandas()
    logging.info(f"Read {len(df)} rows from BigQuery.")

    # --- Step 1: Query existing chunks for all question_ids in the batch ---
    question_ids = df["question_id"].astype(str).unique().tolist()
    existing_names = []

    if question_ids:
        # Use $in operator for batch filtering, with pagination
        # (query_data_objects returns max 100 results per page)
        page_token = None
        while True:
            search_request = vectorsearch_v1beta.QueryDataObjectsRequest(
                parent=collection_path,
                filter={"question_id": {"$in": question_ids}},
                **({"page_token": page_token} if page_token else {}),
            )
            response = search_client.query_data_objects(search_request)
            existing_names.extend(obj.name for obj in response.data_objects)
            if not response.next_page_token:
                break
            page_token = response.next_page_token

    # Separate chunks into: new (to create), unchanged (skip), stale (to delete).
    # Extract chunk_id from resource name (format: .../dataObjects/{chunk_id})
    existing_chunk_ids = {name.rsplit("/", 1)[-1] for name in existing_names}
    new_chunk_ids = set(df["chunk_id"].astype(str))

    # To create = in current batch but not yet in VS
    df_to_create = df[~df["chunk_id"].astype(str).isin(existing_chunk_ids)]
    # Stale = in VS but not in the current batch (orphaned from old runs)
    stale_names = [
        n for n in existing_names if n.rsplit("/", 1)[-1] not in new_chunk_ids
    ]

    logging.info(
        f"Found {len(existing_names)} existing chunks. "
        f"{len(df_to_create)} new to create, "
        f"{len(stale_names)} stale to delete, "
        f"{len(existing_chunk_ids & new_chunk_ids)} unchanged."
    )

    # --- Step 2: Create new chunks FIRST (safe — unique timestamped IDs) ---
    created = 0
    batch_size = min(
        ingestion_batch_size, 250
    )  # Max 250 per request for auto-embeddings
    for batch_start in range(0, len(df_to_create), batch_size):
        batch_end = min(batch_start + batch_size, len(df_to_create))
        batch_df = df_to_create.iloc[batch_start:batch_end]

        batch_request = [
            {
                "data_object_id": str(row["chunk_id"]),
                "data_object": {
                    "data": {
                        "question_id": str(row["question_id"]),
                        "text_chunk": str(row["text_chunk"]),
                        "full_text_md": str(row["full_text_md"]),
                    },
                    "vectors": {},  # Empty vectors — auto-generated by VS 2.0
                },
            }
            for _, row in batch_df.iterrows()
        ]

        request = vectorsearch_v1beta.BatchCreateDataObjectsRequest(
            parent=collection_path,
            requests=batch_request,
        )
        data_object_client.batch_create_data_objects(request)
        created += len(batch_df)

        if (batch_start // batch_size + 1) % 10 == 0:
            logging.info(f"Created {batch_end}/{len(df_to_create)} data objects...")

    logging.info(f"Creation phase complete. {created} new chunks created.")

    # --- Step 3: Delete stale chunks AFTER new ones are safely created ---
    # Only removes chunks whose IDs are NOT in the current batch
    total_deleted = 0
    if stale_names:
        for i in range(0, len(stale_names), 1000):  # API limit: 1000 per request
            batch_names = stale_names[i : i + 1000]
            delete_requests = [
                vectorsearch_v1beta.DeleteDataObjectRequest(name=name)
                for name in batch_names
            ]
            delete_request = vectorsearch_v1beta.BatchDeleteDataObjectsRequest(
                parent=collection_path,
                requests=delete_requests,
            )
            data_object_client.batch_delete_data_objects(delete_request)

        total_deleted = len(stale_names)

    logging.info(
        f"Ingestion complete. {created} chunks created, {total_deleted} stale chunks removed."
    )
