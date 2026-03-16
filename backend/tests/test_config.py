import os
from app.config import Settings

def test_default_data_dir():
    s = Settings()
    assert s.data_dir == "/data"

def test_cors_origins_default():
    s = Settings()
    assert "http://localhost:5173" in s.cors_origins
    assert "http://localhost" in s.cors_origins

def test_data_dir_override(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/tmp/test-data")
    s = Settings()
    assert s.data_dir == "/tmp/test-data"
