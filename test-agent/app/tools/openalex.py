import requests

def search_openalex(query: str, entity_type: str = "works"):
    """
    Searches the OpenAlex database for a given query.

    Args:
        query: The search term (e.g., paper title, author name, concept).
        entity_type: The type of entity to search for. Can be one of:
                     "works", "authors", "venues", "institutions", "concepts".
                     Defaults to "works".

    Returns:
        A JSON object containing the search results from the OpenAlex API.
        Returns an error message if the request fails.
    """
    base_url = "https://api.openalex.org"
    search_url = f"{base_url}/{entity_type}?search={query}"

    try:
        response = requests.get(search_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
