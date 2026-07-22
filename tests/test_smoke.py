from pathlib import Path


def test_app_file_exists():
    assert Path("app.py").exists()


def test_version_and_rebirth_defaults_are_present():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.1.0"' in source
    assert '"Rebirth Island"' in source
    assert "DEFAULT_DURATION = 10 * 60" in source


def test_launcher_and_manifest_exist():
    assert Path("Start Rebirth Checker.bat").exists()
    assert Path("turbo-project.json").exists()
