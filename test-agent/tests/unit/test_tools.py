import unittest
from unittest.mock import patch, MagicMock
import requests

from app.tools.openalex import search_openalex

class TestOpenAlexTool(unittest.TestCase):

    @patch('app.tools.openalex.requests.get')
    def test_search_openalex_success(self, mock_get):
        """
        Tests a successful call to the search_openalex tool.
        """
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"id": "W123", "display_name": "Test Paper"}]}
        mock_get.return_value = mock_response

        # Call the function
        query = "test query"
        result = search_openalex(query)

        # Assertions
        mock_get.assert_called_once_with("https://api.openalex.org/works?search=test query")
        self.assertEqual(result, {"results": [{"id": "W123", "display_name": "Test Paper"}]})

    @patch('app.tools.openalex.requests.get')
    def test_search_openalex_http_error(self, mock_get):
        """
        Tests the tool's behavior on an HTTP error.
        """
        # Configure the mock to raise an exception
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("HTTP Error")
        mock_get.return_value = mock_response

        # Call the function
        query = "error query"
        result = search_openalex(query)

        # Assertions
        mock_get.assert_called_once_with("https://api.openalex.org/works?search=error query")
        self.assertIn("An error occurred", result)

    @patch('app.tools.openalex.requests.get')
    def test_search_openalex_entity_type(self, mock_get):
        """
        Tests that the entity_type parameter is correctly used in the URL.
        """
        # Configure the mock for a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        # Call the function with a different entity type
        query = "author query"
        entity_type = "authors"
        search_openalex(query, entity_type)

        # Assertions
        mock_get.assert_called_once_with("https://api.openalex.org/authors?search=author query")

if __name__ == '__main__':
    unittest.main()
