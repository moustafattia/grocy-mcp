"""Tests for configuration loading."""

import os
from unittest.mock import patch

from grocy_mcp.config import load_config


def test_config_from_env():
    with patch.dict(os.environ, {"GROCY_URL": "http://localhost:9192", "GROCY_API_KEY": "testkey"}):
        config = load_config()
    assert config.url == "http://localhost:9192"
    assert config.api_key == "testkey"


def test_config_missing_url_raises():
    with patch.dict(os.environ, {}, clear=True):
        try:
            load_config()
            assert False, "Should have raised"
        except ValueError as e:
            assert "GROCY_URL" in str(e)
            assert "--url" not in str(e)


def test_config_missing_api_key_raises():
    with patch.dict(os.environ, {"GROCY_URL": "http://localhost:9192"}, clear=True):
        try:
            load_config()
            assert False, "Should have raised"
        except ValueError as e:
            assert "GROCY_API_KEY" in str(e)
            assert "--api-key" not in str(e)


def test_config_overrides():
    with patch.dict(os.environ, {"GROCY_URL": "http://env-url", "GROCY_API_KEY": "envkey"}):
        config = load_config(url="http://override-url")
    assert config.url == "http://override-url"
    assert config.api_key == "envkey"
