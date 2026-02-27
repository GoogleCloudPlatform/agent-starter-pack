#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click",
#     "google-cloud-vectorsearch",
# ]
# ///
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

"""Deletes a Vector Search 2.0 Collection and all its data objects."""

import sys

import click
from google.api_core import exceptions
from google.cloud import vectorsearch_v1beta


@click.command()
@click.argument("project_id")
@click.argument("location")
@click.argument("collection_id")
def main(project_id: str, location: str, collection_id: str) -> None:
    """Delete a Vector Search 2.0 Collection."""
    client = vectorsearch_v1beta.VectorSearchServiceClient()
    collection_name = (
        f"projects/{project_id}/locations/{location}/collections/{collection_id}"
    )

    click.echo(f"Deleting collection: {collection_name}")

    try:
        client.delete_collection(
            request=vectorsearch_v1beta.DeleteCollectionRequest(name=collection_name)
        )
        click.echo("Collection deleted successfully.")
    except exceptions.NotFound:
        click.echo("Collection not found (already deleted).")
    except Exception as e:
        click.echo(f"Error deleting collection: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
