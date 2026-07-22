import importlib.util
from pathlib import Path


def test_app_file_exists():
    assert Path("app.py").exists()


def test_app_imports():
    spec = importlib.util.spec_from_file_location("rebirthchecker_app", "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.APP_VERSION == "0.1.0"
    assert "Rebirth Island" in module.DEFAULT_MAPS


def test_default_duration_is_ten_minutes():
    spec = importlib.util.spec_from_file_location("rebirthchecker_app", "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.DEFAULT_DURATION == 600
