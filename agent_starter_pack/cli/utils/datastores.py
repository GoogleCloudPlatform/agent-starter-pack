"""Datastore types and descriptions for data ingestion."""

# Dictionary mapping datastore types to their descriptions
DATASTORES = {
    "vertex_ai_search": {
        "name": "Vertex AI Search",
        "description": "Managed, serverless document store that enables Google-quality search and RAG for generative AI.",
    },
    "vertex_ai_vector_search": {
        "name": "Vertex AI Vector Search",
        "description": "Scalable vector search engine for building search, recommendation systems, and generative AI applications. Based on ScaNN algorithm.",
    },
}

DATASTORE_TYPES = list(DATASTORES.keys())


def get_datastore_info(datastore_type: str) -> dict:
    """Get information about a datastore type.

    Args:
        datastore_type: The datastore type key

    Returns:
        Dictionary with datastore information

    Raises:
        ValueError: If the datastore type is not valid
    """
    if datastore_type not in DATASTORES:
        raise ValueError(f"Invalid datastore type: {datastore_type}")
    return DATASTORES[datastore_type]
