import importlib.util
from pathlib import Path


def load_app_module():
    spec = importlib.util.spec_from_file_location("rebirthchecker_app", "app.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_file_exists():
    assert Path("app.py").exists()


def test_app_imports():
    module = load_app_module()
    assert module.APP_VERSION == "0.2.0"
    assert "Rebirth Island" in module.DEFAULT_MAPS


def test_default_duration_is_ten_minutes():
    module = load_app_module()
    assert module.DEFAULT_DURATION == 600


def test_rotation_order_starts_with_rebirth():
    module = load_app_module()
    assert module.DEFAULT_MAPS[0] == "Rebirth Island"
