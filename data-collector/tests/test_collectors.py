"""Tests for data collectors: web crawler, API fetcher, file reader."""

from io import StringIO
from unittest.mock import AsyncMock, Mock, patch

import httpx
from data_collector.collectors.api_fetcher import APIFetcher
from data_collector.collectors.file_reader import FileReader
from data_collector.collectors.web_crawler import WebCrawler


class TestWebCrawler:
    """Test web crawler."""

    async def test_crawl_success(self):
        """Test successful page crawl."""
        crawler = WebCrawler()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <p>Hello World</p>
                <a href="https://example.com/page1">Link 1</a>
                <a href="https://example.com/page2">Link 2</a>
            </body>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await crawler.crawl("https://example.com")

            assert result.success is True
            assert result.status_code == 200
            assert result.title == "Test Page"
            assert "Hello World" in result.text_content
            assert len(result.links) == 2
            assert "https://example.com/page1" in result.links

    async def test_crawl_removes_script_and_style(self):
        """Test that script and style tags are removed."""
        crawler = WebCrawler()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <title>Test</title>
                <script>alert('test');</script>
                <style>.hidden { display: none; }</style>
            </head>
            <body>
                <p>Visible text</p>
                <script>console.log('remove me');</script>
            </body>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await crawler.crawl("https://example.com")

            assert result.success is True
            assert "Visible text" in result.text_content
            assert "alert" not in result.text_content
            assert "console.log" not in result.text_content
            assert ".hidden" not in result.text_content

    async def test_crawl_http_error(self):
        """Test handling of HTTP error status."""
        crawler = WebCrawler()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await crawler.crawl("https://example.com/notfound")

            assert result.success is False
            assert result.status_code == 404
            assert result.error == "HTTP 404"

    async def test_crawl_network_error(self):
        """Test handling of network errors."""
        crawler = WebCrawler()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )

            result = await crawler.crawl("https://example.com")

            assert result.success is False
            assert result.status_code == 0
            assert "Connection failed" in result.error

    async def test_crawl_extracts_links(self):
        """Test link extraction."""
        crawler = WebCrawler()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <a href="https://example.com/1">Link 1</a>
                <a href="/relative">Relative</a>
                <a href="https://example.com/2">Link 2</a>
                <a>No href</a>
            </body>
        </html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await crawler.crawl("https://example.com")

            assert result.success is True
            # Should only extract absolute URLs starting with http
            assert len(result.links) == 2
            assert "https://example.com/1" in result.links
            assert "https://example.com/2" in result.links

    async def test_crawl_limits_links(self):
        """Test that links are limited to 50."""
        crawler = WebCrawler()
        links_html = "\n".join(
            [f'<a href="https://example.com/{i}">Link {i}</a>' for i in range(100)]
        )
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = f"<html><body>{links_html}</body></html>"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await crawler.crawl("https://example.com")

            assert result.success is True
            assert len(result.links) == 50


class TestAPIFetcher:
    """Test API fetcher."""

    async def test_get_json_response(self):
        """Test GET request with JSON response."""
        fetcher = APIFetcher()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.is_success = True
        mock_response.json.return_value = {"status": "ok", "data": [1, 2, 3]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetcher.get("https://api.example.com/data")

            assert result.success is True
            assert result.status_code == 200
            assert result.data == {"status": "ok", "data": [1, 2, 3]}
            assert "json" in result.content_type

    async def test_get_text_response(self):
        """Test GET request with text response."""
        fetcher = APIFetcher()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.is_success = True
        mock_response.text = "Plain text response"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetcher.get("https://api.example.com/text")

            assert result.success is True
            assert result.data == "Plain text response"

    async def test_get_with_headers_and_params(self):
        """Test GET with custom headers and params."""
        fetcher = APIFetcher()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.is_success = True
        mock_response.json.return_value = {"result": "success"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            headers = {"Authorization": "Bearer token"}
            params = {"page": 1, "limit": 10}
            result = await fetcher.get(
                "https://api.example.com/data", headers=headers, params=params
            )

            assert result.success is True
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"] == headers
            assert call_kwargs["params"] == params

    async def test_post_json(self):
        """Test POST request with JSON data."""
        fetcher = APIFetcher()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.is_success = True
        mock_response.json.return_value = {"id": 123, "created": True}

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            json_data = {"name": "Test", "value": 42}
            result = await fetcher.post("https://api.example.com/create", json_data=json_data)

            assert result.success is True
            assert result.status_code == 201
            assert result.data["id"] == 123
            mock_post.assert_called_once()

    async def test_get_request_error(self):
        """Test handling of network errors in GET."""
        fetcher = APIFetcher()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            result = await fetcher.get("https://api.example.com/data")

            assert result.success is False
            assert result.status_code == 0
            assert "Network error" in result.error

    async def test_post_request_error(self):
        """Test handling of network errors in POST."""
        fetcher = APIFetcher()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Connection timeout")
            )

            result = await fetcher.post("https://api.example.com/create", json_data={})

            assert result.success is False
            assert result.error == "Connection timeout"


class TestFileReader:
    """Test file reader."""

    def test_read_csv(self):
        """Test reading CSV file."""
        reader = FileReader()
        _csv_content = "name,age,city\nAlice,30,Seoul\nBob,25,Busan\n"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pandas.read_csv") as mock_read_csv:
                import pandas as pd

                df = pd.DataFrame(
                    {
                        "name": ["Alice", "Bob"],
                        "age": [30, 25],
                        "city": ["Seoul", "Busan"],
                    }
                )
                mock_read_csv.return_value = df

                result = reader.read("test.csv")

                assert result.success is True
                assert result.file_type == "csv"
                assert result.row_count == 2
                assert result.columns == ["name", "age", "city"]
                assert len(result.data) == 2

    def test_read_excel(self):
        """Test reading Excel file."""
        reader = FileReader()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pandas.read_excel") as mock_read_excel:
                import pandas as pd

                df = pd.DataFrame({"product": ["A", "B"], "price": [100, 200]})
                mock_read_excel.return_value = df

                result = reader.read("test.xlsx")

                assert result.success is True
                assert result.file_type == "excel"
                assert result.row_count == 2
                assert "product" in result.columns

    def test_read_json_array(self):
        """Test reading JSON file with array."""
        reader = FileReader()
        json_content = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=StringIO(json_content)):
                result = reader.read("test.json")

                assert result.success is True
                assert result.file_type == "json"
                assert result.row_count == 2
                assert result.columns == ["id", "name"]
                assert len(result.data) == 2

    def test_read_json_object(self):
        """Test reading JSON file with single object."""
        reader = FileReader()
        json_content = '{"id": 1, "name": "Alice", "active": true}'

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=StringIO(json_content)):
                result = reader.read("test.json")

                assert result.success is True
                assert result.row_count == 1
                assert "id" in result.columns
                assert result.data[0]["name"] == "Alice"

    def test_read_jsonl(self):
        """Test reading JSONL file."""
        reader = FileReader()
        jsonl_content = (
            '{"id": 1, "name": "Alice"}\n{"id": 2, "name": "Bob"}\n{"id": 3, "name": "Charlie"}\n'
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=StringIO(jsonl_content)):
                result = reader.read("test.jsonl")

                assert result.success is True
                assert result.file_type == "jsonl"
                assert result.row_count == 3
                assert result.columns == ["id", "name"]

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        reader = FileReader()

        with patch("pathlib.Path.exists", return_value=False):
            result = reader.read("notfound.csv")

            assert result.success is False
            assert "File not found" in result.error

    def test_read_unsupported_extension(self):
        """Test reading file with unsupported extension."""
        reader = FileReader()

        with patch("pathlib.Path.exists", return_value=True):
            result = reader.read("test.txt")

            assert result.success is False
            assert "Unsupported" in result.error

    def test_read_csv_limits_to_1000_rows(self):
        """Test that CSV reading limits to 1000 rows."""
        reader = FileReader()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pandas.read_csv") as mock_read_csv:
                import pandas as pd

                # Create a dataframe with 2000 rows
                df = pd.DataFrame({"col": range(2000)})
                mock_read_csv.return_value = df

                result = reader.read("test.csv")

                assert result.success is True
                assert result.row_count == 2000  # Reports total
                assert len(result.data) == 1000  # But only returns first 1000

    def test_read_jsonl_limits_to_1000_rows(self):
        """Test that JSONL reading limits to 1000 rows."""
        reader = FileReader()
        # Generate 1500 lines
        jsonl_lines = "\n".join([f'{{"id": {i}}}' for i in range(1500)])

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=StringIO(jsonl_lines)):
                result = reader.read("test.jsonl")

                assert result.success is True
                # Should stop at 1000
                assert len(result.data) == 1000

    def test_supported_extensions(self):
        """Test supported file extensions."""
        reader = FileReader()

        expected = {".csv", ".xlsx", ".xls", ".json", ".jsonl"}
        assert reader.SUPPORTED_EXTENSIONS == expected
