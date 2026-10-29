from pathlib import Path


def test_app_file_exists():
    assert Path("app.py").exists()


def test_version_and_rebirth_defaults_are_present():
    source = Path("app.py").read_text(encoding="utf-8")
    version = Path("VERSION").read_text().strip()
    assert f'APP_VERSION = "{version}"' in source
    assert '"Rebirth Island"' in source
    from test_app import load_app_module
    assert load_app_module().DEFAULT_DURATION == 10 * 60


def test_launcher_and_manifest_exist():
    assert Path("Start Rebirth Checker.bat").exists()
    assert Path("turbo-project.json").exists()
