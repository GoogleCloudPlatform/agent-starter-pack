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

    For each question_id in the current batch, deletes any existing chunks
    from Vector Search, then creates the new chunks. This ensures updated
    documents replace stale content instead of being silently skipped.

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

    # Delete existing chunks for all question_ids in the batch
    question_ids = df["question_id"].astype(str).unique().tolist()
    total_deleted = 0

    if question_ids:
        # Query all existing chunks using $in operator, handling pagination
        existing_names = []
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

        if existing_names:
            # Delete in batches of 1000 (API limit)
            for i in range(0, len(existing_names), 1000):
                batch_names = existing_names[i : i + 1000]
                delete_requests = [
                    vectorsearch_v1beta.DeleteDataObjectRequest(name=name)
                    for name in batch_names
                ]
                delete_request = vectorsearch_v1beta.BatchDeleteDataObjectsRequest(
                    parent=collection_path,
                    requests=delete_requests,
                )
                data_object_client.batch_delete_data_objects(delete_request)

            total_deleted = len(existing_names)

    logging.info(f"Deletion phase complete. {total_deleted} old chunks removed.")

    # Batch create new data objects in Vector Search 2.0
    # Max 250 per request for auto-embeddings
    created = 0
    batch_size = min(ingestion_batch_size, 250)
    for batch_start in range(0, len(df), batch_size):
        batch_end = min(batch_start + batch_size, len(df))
        batch_df = df.iloc[batch_start:batch_end]

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
            logging.info(f"Processed {batch_end}/{len(df)} data objects...")

    logging.info(f"Ingestion complete. {created} chunks created.")
