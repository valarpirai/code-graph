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

def test_get_settings_returns_same_instance():
    from app.config import get_settings
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2  # LRU cache returns same object
