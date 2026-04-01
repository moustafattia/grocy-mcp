"""Tests for file helpers."""

import base64
from unittest.mock import AsyncMock

from grocy_mcp.core.files import file_download_data, file_upload_data


async def test_file_download_data_encodes_content_base64():
    client = AsyncMock()
    client.download_file.return_value = (b"hello", "text/plain")

    result = await file_download_data(client, "productpictures", "milk.jpg")

    assert result["group"] == "productpictures"
    assert result["file_name"] == "milk.jpg"
    assert result["content_type"] == "text/plain"
    assert base64.b64decode(result["content_base64"].encode("ascii")) == b"hello"


async def test_file_upload_data_decodes_base64():
    client = AsyncMock()
    content_base64 = base64.b64encode(b"hello").decode("ascii")

    result = await file_upload_data(client, "productpictures", "milk.jpg", content_base64)

    client.upload_file.assert_awaited_once()
    assert result == {"group": "productpictures", "file_name": "milk.jpg", "uploaded": True}
